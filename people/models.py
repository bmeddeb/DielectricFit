import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class ProjectRole(models.TextChoices):
    OWNER = "owner", "Owner"
    ADMIN = "admin", "Administrator" 
    MEMBER = "member", "Member"
    VIEWER = "viewer", "Viewer"


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
        """Check if user can edit project settings"""
        return self.role in [ProjectRole.OWNER, ProjectRole.ADMIN]
    
    def can_upload(self):
        """Check if user can upload datasets"""
        return self.role in [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.MEMBER]
    
    def can_delete_datasets(self):
        """Check if user can delete any dataset in project"""
        return self.role in [ProjectRole.OWNER, ProjectRole.ADMIN]


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
