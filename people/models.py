import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class ProjectRole(models.TextChoices):
    # Personal Project Roles (GitHub style)
    OWNER = "owner", "Owner"
    COLLABORATOR = "collaborator", "Collaborator"
    
    # Organization-style Granular Roles (GitHub style)
    READ = "read", "Read"           # View and discuss datasets/analyses
    TRIAGE = "triage", "Triage"     # Manage issues and discussions
    WRITE = "write", "Write"        # Upload datasets, run analyses
    MAINTAIN = "maintain", "Maintain" # Manage project settings
    ADMIN = "admin", "Admin"        # Full access including deletion
    
    # Legacy roles (deprecated but kept for backwards compatibility)
    MEMBER = "member", "Member"     # Maps to WRITE
    VIEWER = "viewer", "Viewer"     # Maps to READ


class ProjectVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    INTERNAL = "internal", "Internal"
    PUBLIC = "public", "Public"


class Project(models.Model):
    """Project model for organizing datasets and managing access control."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=16, 
        choices=ProjectVisibility.choices, 
        default=ProjectVisibility.PRIVATE
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata fields
    dataset_count = models.IntegerField(default=0)
    total_data_points = models.BigIntegerField(default=0)
    last_activity_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["created_by", "created_at"], name="idx_people_proj_creator"),
            models.Index(fields=["visibility", "created_at"], name="idx_people_proj_visibility"),
            models.Index(fields=["last_activity_at"], name="idx_people_proj_activity"),
        ]
        
    def __str__(self):
        return self.name
    
    @property
    def is_archived(self):
        return self.archived_at is not None
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])
        
    def update_metadata(self):
        """Update project metadata (dataset count, total points)"""
        # Import here to avoid circular imports
        from dielectric.models import Dataset
        datasets = Dataset.objects.filter(project=self)
        self.dataset_count = datasets.count()
        self.total_data_points = sum(d.row_count or 0 for d in datasets)
        self.save(update_fields=['dataset_count', 'total_data_points'])
    
    def get_user_membership(self, user):
        """Get user's membership in this project"""
        try:
            return self.memberships.get(user=user)
        except ProjectMembership.DoesNotExist:
            return None
    
    def user_can_view(self, user):
        """Check if user can view this project"""
        if not user.is_authenticated:
            return self.visibility == ProjectVisibility.PUBLIC
        
        # Check membership
        membership = self.get_user_membership(user)
        if membership:
            return True
            
        # Check visibility
        return self.visibility in [ProjectVisibility.PUBLIC, ProjectVisibility.INTERNAL]
    
    def user_can_upload(self, user):
        """Check if user can upload datasets to this project"""
        if not user.is_authenticated:
            return False
            
        membership = self.get_user_membership(user)
        return membership and membership.can_upload()
    
    def user_can_delete_datasets(self, user):
        """Check if user can delete datasets in this project"""
        if not user.is_authenticated:
            return False
            
        membership = self.get_user_membership(user)
        return membership and membership.can_delete_datasets()
    
    def user_can_edit(self, user):
        """Check if user can edit project settings"""
        if not user.is_authenticated:
            return False
            
        membership = self.get_user_membership(user)
        return membership and membership.can_edit()
    
    # GitHub-style permission methods
    def user_can_read(self, user):
        """GitHub READ permission: View and discuss datasets/analyses"""
        return self.user_can_view(user)
    
    def user_can_triage(self, user):
        """GitHub TRIAGE permission: Manage issues and discussions (future feature)"""
        if not user.is_authenticated:
            return False
        membership = self.get_user_membership(user)
        if not membership:
            return False
        return membership.role in [
            ProjectRole.TRIAGE, ProjectRole.WRITE, ProjectRole.MAINTAIN, 
            ProjectRole.ADMIN, ProjectRole.OWNER
        ]
    
    def user_can_write(self, user):
        """GitHub WRITE permission: Upload datasets, run analyses"""
        return self.user_can_upload(user)
    
    def user_can_maintain(self, user):
        """GitHub MAINTAIN permission: Manage project settings, invite users"""
        if not user.is_authenticated:
            return False
        membership = self.get_user_membership(user)
        if not membership:
            return False
        return membership.role in [
            ProjectRole.MAINTAIN, ProjectRole.ADMIN, ProjectRole.OWNER
        ]
    
    def user_can_admin(self, user):
        """GitHub ADMIN permission: Full access including member management"""
        if not user.is_authenticated:
            return False
        membership = self.get_user_membership(user)
        if not membership:
            return False
        return membership.role in [ProjectRole.ADMIN, ProjectRole.OWNER]
    
    def user_can_own(self, user):
        """OWNER permission: Delete project, transfer ownership"""
        if not user.is_authenticated:
            return False
        membership = self.get_user_membership(user)
        return membership and membership.role == ProjectRole.OWNER
    
    def user_can_invite(self, user):
        """Check if user can invite others to project"""
        return self.user_can_maintain(user)
    
    def user_can_manage_members(self, user):
        """Check if user can manage project members"""
        return self.user_can_admin(user)
    
    def get_user_effective_role(self, user):
        """Get user's effective role for this project"""
        if not user.is_authenticated:
            if self.visibility == ProjectVisibility.PUBLIC:
                return ProjectRole.READ
            return None
            
        membership = self.get_user_membership(user)
        if membership:
            return membership.role
            
        # Non-members with internal/public access get READ
        if self.visibility in [ProjectVisibility.PUBLIC, ProjectVisibility.INTERNAL]:
            return ProjectRole.READ
            
        return None


class UserProjectPreference(models.Model):
    """Track user's project preferences and active project"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_preference"
    )
    active_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="active_for_users"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s preferences"


class ProjectMembership(models.Model):
    """User membership in projects with roles and permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="project_memberships"
    )
    role = models.CharField(max_length=16, choices=ProjectRole.choices)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sent_project_invitations"
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Access tracking
    last_accessed_at = models.DateTimeField(null=True, blank=True)
    access_count = models.IntegerField(default=0)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                name="uq_people_project_membership"
            )
        ]
        indexes = [
            models.Index(fields=["user", "joined_at"], name="idx_people_member_user"),
            models.Index(fields=["project", "role"], name="idx_people_member_role"),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.project.name} ({self.role})"
    
    def track_access(self):
        """Track user access to project"""
        self.last_accessed_at = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed_at', 'access_count'])
    
    def can_edit(self):
        """Check if user can edit project settings (legacy method)"""
        return self.role in [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.MAINTAIN]
    
    def can_upload(self):
        """Check if user can upload datasets (legacy method)"""
        return self.role in [
            ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.MAINTAIN,
            ProjectRole.WRITE, ProjectRole.COLLABORATOR, ProjectRole.MEMBER  # Legacy support
        ]
    
    def can_delete_datasets(self):
        """Check if user can delete any dataset in project (legacy method)"""
        return self.role in [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.MAINTAIN, ProjectRole.WRITE]
    
    # GitHub-style permission methods
    def has_read_permission(self):
        """All members have read permission"""
        return True
    
    def has_triage_permission(self):
        """Can manage issues and discussions"""
        return self.role in [
            ProjectRole.TRIAGE, ProjectRole.WRITE, ProjectRole.MAINTAIN, 
            ProjectRole.ADMIN, ProjectRole.OWNER, ProjectRole.COLLABORATOR,
            ProjectRole.MEMBER  # Legacy support
        ]
    
    def has_write_permission(self):
        """Can upload datasets, run analyses"""
        return self.can_upload()
    
    def has_maintain_permission(self):
        """Can manage project settings, invite users"""
        return self.role in [
            ProjectRole.MAINTAIN, ProjectRole.ADMIN, ProjectRole.OWNER
        ]
    
    def has_admin_permission(self):
        """Full access including member management"""
        return self.role in [ProjectRole.ADMIN, ProjectRole.OWNER]
    
    def has_owner_permission(self):
        """Can delete project, transfer ownership"""
        return self.role == ProjectRole.OWNER
    
    def can_invite_users(self):
        """Can send project invitations"""
        return self.has_maintain_permission()
    
    def can_manage_members(self):
        """Can manage project memberships"""
        return self.has_admin_permission()


class ProjectActivity(models.Model):
    """Track project activity history and audit trail"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=64)  # 'upload', 'delete', 'analyze', 'invite', etc.
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)  # Additional context (dataset_id, file_name, etc.)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "project activity"
        verbose_name_plural = "project activities"
        indexes = [
            models.Index(fields=["project", "created_at"], name="idx_people_act_project"),
            models.Index(fields=["user", "created_at"], name="idx_people_act_user"),
        ]
        
    def __str__(self):
        return f"{self.user.username} {self.action} in {self.project.name}"


class UserProfile(models.Model):
    """Extended user profile information"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    phone = models.CharField(max_length=20, blank=True, default="")
    timezone = models.CharField(max_length=50, default="UTC")
    bio = models.TextField(blank=True, default="")
    # avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)  # Requires Pillow
    email_notifications = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class ProjectInvitationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"
    EXPIRED = "expired", "Expired"


class ProjectInvitation(models.Model):
    """GitHub-style project invitations with secure token system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='sent_invitations'
    )
    
    # Can invite existing users or email addresses
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='received_invitations',
        null=True, blank=True
    )
    email = models.EmailField()  # Email for the invitation (may be for non-user)
    role = models.CharField(max_length=20, choices=ProjectRole.choices)
    message = models.TextField(blank=True, default="")
    
    # Status and token system
    status = models.CharField(
        max_length=20, 
        choices=ProjectInvitationStatus.choices, 
        default=ProjectInvitationStatus.PENDING
    )
    token = models.CharField(max_length=64, unique=True)  # Secure invitation token
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # 7 days from creation
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = [('project', 'email')]  # One invitation per email per project
        indexes = [
            models.Index(fields=['token'], name='idx_people_invitation_token'),
            models.Index(fields=['email', 'status'], name='idx_people_invitation_email'),
            models.Index(fields=['project', 'status'], name='idx_people_invitation_project'),
        ]
        verbose_name = "project invitation"
        verbose_name_plural = "project invitations"
    
    def save(self, *args, **kwargs):
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
            
        # If invited_user is provided, use their email
        if self.invited_user and not self.email:
            self.email = self.invited_user.email
            
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if invitation has expired"""
        return timezone.now() > self.expires_at
    
    def can_accept(self):
        """Check if invitation can be accepted"""
        return (
            self.status == ProjectInvitationStatus.PENDING and 
            not self.is_expired()
        )
    
    def accept(self, user):
        """Accept invitation and create membership"""
        if not self.can_accept():
            raise ValidationError("Invitation cannot be accepted")
            
        if self.email.lower() != user.email.lower():
            raise ValidationError("Email mismatch")
        
        # Create or update membership
        membership, created = ProjectMembership.objects.get_or_create(
            project=self.project,
            user=user,
            defaults={'role': self.role}
        )
        
        if not created:
            # Update existing membership role if invitation role is higher
            membership.role = self.role
            membership.save()
        
        # Mark invitation as accepted
        self.status = ProjectInvitationStatus.ACCEPTED
        self.responded_at = timezone.now()
        self.invited_user = user
        self.save()
        
        return membership
    
    def decline(self):
        """Decline invitation"""
        if self.status != ProjectInvitationStatus.PENDING:
            raise ValidationError("Only pending invitations can be declined")
            
        self.status = ProjectInvitationStatus.DECLINED
        self.responded_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.email} invited to {self.project.name} as {self.get_role_display()}"
