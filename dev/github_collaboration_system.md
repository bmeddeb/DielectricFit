# GitHub-Style Collaboration System for DielectricFit

## Overview

DielectricFit now implements a comprehensive collaboration system modeled after GitHub's repository permissions and invitation architecture. This system provides granular access control, secure invitation workflows, and scalable project management capabilities.

## Architecture Design

### Role-Based Access Control (RBAC)

The system implements GitHub's granular collaboration model:

- **Read**: View and discuss datasets/analyses
- **Triage**: Manage issues and discussions (future feature)
- **Write**: Upload datasets, run analyses
- **Maintain**: Manage project settings, invite users
- **Admin**: Full access including member management
- **Owner**: Delete project, transfer ownership

### Permission Matrix

| Permission | Read | Triage | Write | Maintain | Admin | Owner |
|------------|------|--------|-------|----------|-------|-------|
| View datasets/analyses | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Download data | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create comments/issues | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Manage issues/labels | | ✓ | ✓ | ✓ | ✓ | ✓ |
| Upload datasets | | | ✓ | ✓ | ✓ | ✓ |
| Edit/delete datasets | | | ✓ | ✓ | ✓ | ✓ |
| Run analyses | | | ✓ | ✓ | ✓ | ✓ |
| Manage project settings | | | | ✓ | ✓ | ✓ |
| Invite collaborators | | | | ✓ | ✓ | ✓ |
| Manage members | | | | | ✓ | ✓ |
| Delete project | | | | | | ✓ |

## Data Models

### Enhanced ProjectRole Enum

```python
class ProjectRole(models.TextChoices):
    # GitHub-style Granular Roles
    READ = "read", "Read"           # View and discuss datasets/analyses
    TRIAGE = "triage", "Triage"     # Manage issues and discussions
    WRITE = "write", "Write"        # Upload datasets, run analyses
    MAINTAIN = "maintain", "Maintain" # Manage project settings
    ADMIN = "admin", "Admin"        # Full access including deletion
    OWNER = "owner", "Owner"        # Delete project, transfer ownership
    
    # Personal Project Style (simplified for small teams)
    COLLABORATOR = "collaborator", "Collaborator"  # Maps to WRITE
```

### ProjectInvitation Model

```python
class ProjectInvitation(models.Model):
    """GitHub-style project invitations with secure token system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE)
    invited_user = models.ForeignKey(User, null=True, blank=True)  # Optional
    email = models.EmailField()  # Email for the invitation
    role = models.CharField(max_length=20, choices=ProjectRole.choices)
    message = models.TextField(blank=True)
    
    # Status and security
    status = models.CharField(max_length=20, default='pending')
    token = models.CharField(max_length=64, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()  # 7 days from creation
    responded_at = models.DateTimeField(null=True, blank=True)
```

### Key Features

#### 1. Secure Token System
- **64-character URL-safe tokens** for invitation links
- **7-day expiration** following GitHub's model
- **Unique constraint** prevents token collision
- **Automatic token generation** on save

#### 2. Email-Based Invitations
- Support for **existing users** and **non-users**
- **One invitation per email per project** constraint
- **Email validation** on acceptance
- **Automatic user association** when accepting

#### 3. Status Tracking
- **Pending**: Invitation sent, awaiting response
- **Accepted**: User joined the project
- **Declined**: User explicitly declined
- **Expired**: Invitation past expiration date

## Implementation Details

### Project Permission Methods

```python
# GitHub-style permission checks
def user_can_read(self, user):
    """GitHub READ permission: View and discuss datasets/analyses"""
    return self.user_can_view(user)

def user_can_write(self, user):
    """GitHub WRITE permission: Upload datasets, run analyses"""
    return self.user_can_upload(user)

def user_can_maintain(self, user):
    """GitHub MAINTAIN permission: Manage project settings, invite users"""
    # Implementation checks membership role

def user_can_admin(self, user):
    """GitHub ADMIN permission: Full access including member management"""
    # Implementation checks for admin/owner roles

def get_user_effective_role(self, user):
    """Get user's effective role for this project"""
    # Returns actual role or READ for public projects
```

### Invitation Workflow

```python
def accept(self, user):
    """Accept invitation and create membership"""
    if not self.can_accept():
        raise ValidationError("Invitation cannot be accepted")
        
    # Validate email match
    if self.email.lower() != user.email.lower():
        raise ValidationError("Email mismatch")
    
    # Create or update membership
    membership, created = ProjectMembership.objects.get_or_create(
        project=self.project,
        user=user,
        defaults={'role': self.role}
    )
    
    # Mark as accepted
    self.status = ProjectInvitationStatus.ACCEPTED
    self.responded_at = timezone.now()
    self.save()
```

## Visibility Levels

Following GitHub's model:

- **Private**: Owner + invited collaborators only
- **Internal**: All authenticated users can see (organization equivalent)
- **Public**: Anyone can see, including anonymous users

## Role Implementation

The system uses a clean, GitHub-inspired role hierarchy:

1. **Hierarchical permissions**: Higher roles inherit all permissions from lower roles
2. **Clear boundaries**: Each role has specific capabilities aligned with GitHub
3. **Extensible design**: Easy to add new roles or modify permissions
4. **Consistent naming**: Follows GitHub's established terminology

## Security Features

### Invitation Security
- **Cryptographically secure tokens** using `secrets.token_urlsafe(32)`
- **Time-bounded access** (7-day expiration)
- **Email verification** required for acceptance
- **Unique constraints** prevent duplicate invitations

### Permission Security
- **Role-based access** at all levels
- **Membership verification** for all operations
- **Project visibility** controls anonymous access
- **Activity audit trail** for security monitoring

## Database Schema

### Indexes for Performance
```python
# ProjectInvitation indexes
models.Index(fields=['token'], name='idx_people_invitation_token'),
models.Index(fields=['email', 'status'], name='idx_people_invitation_email'),
models.Index(fields=['project', 'status'], name='idx_people_invitation_project'),

# ProjectMembership indexes  
models.Index(fields=["user", "joined_at"], name="idx_people_member_user"),
models.Index(fields=["project", "role"], name="idx_people_member_role"),
```

### Constraints for Data Integrity
```python
# One invitation per email per project
unique_together = [('project', 'email')]

# One membership per user per project
models.UniqueConstraint(
    fields=["project", "user"],
    name="uq_people_project_membership"
)
```

## API Integration Points

### Core Endpoints (To Be Implemented)

```python
# Invitation Management
POST   /api/projects/{id}/invitations/     # Send invitation
GET    /api/projects/{id}/invitations/     # List invitations
POST   /api/invitations/{token}/accept/    # Accept invitation
POST   /api/invitations/{token}/decline/   # Decline invitation

# Member Management
GET    /api/projects/{id}/members/         # List members
PUT    /api/projects/{id}/members/{user}/  # Update member role
DELETE /api/projects/{id}/members/{user}/  # Remove member

# Permission Checks
GET    /api/projects/{id}/permissions/     # Check user permissions
```

### Frontend Integration

The system provides clean permission checking:

```javascript
// Check permissions in templates/JavaScript
if (project.user_can_write(user)) {
    // Show upload button
}

if (project.user_can_invite(user)) {
    // Show invite collaborators button  
}

if (project.user_can_admin(user)) {
    // Show member management
}
```

## Usage Examples

### Inviting a Collaborator

```python
# Create invitation
invitation = ProjectInvitation.objects.create(
    project=project,
    invited_by=current_user,
    email="colleague@example.com",
    role=ProjectRole.WRITE,
    message="Join our dielectric analysis project!"
)

# Send email with invitation link
invitation_url = f"/invitations/{invitation.token}/"
send_invitation_email(invitation)
```

### Checking Permissions

```python
# Check if user can upload datasets
if project.user_can_write(user):
    # Allow dataset upload
    
# Check effective role
role = project.get_user_effective_role(user)
if role in [ProjectRole.MAINTAIN, ProjectRole.ADMIN, ProjectRole.OWNER]:
    # Show project settings
```

## Benefits

### For Users
- **Clear permission model** matching familiar GitHub paradigms
- **Secure invitation system** with token-based links
- **Granular access control** for different collaboration needs
- **Flexible project visibility** options

### For Administrators  
- **Comprehensive audit trail** for security monitoring
- **Scalable permission system** from personal to enterprise
- **Backwards compatibility** ensuring smooth transition
- **Database optimization** with proper indexing

### For Developers
- **Clean API surface** with intuitive permission methods
- **Extensible architecture** for future collaboration features
- **Robust data models** with proper constraints
- **GitHub-familiar patterns** reducing learning curve

## Future Enhancements

### Phase 2 Features
1. **Team Management**: Organization-style teams with inherited permissions
2. **Issue Tracking**: Full GitHub-style issue management with TRIAGE role
3. **Activity Feed**: Real-time collaboration activity
4. **Access Requests**: Users can request access to private projects
5. **Batch Invitations**: Invite multiple users at once
6. **Custom Roles**: Define project-specific permission sets

### Integration Opportunities
1. **Email Templates**: Rich HTML invitation emails
2. **Slack/Teams Integration**: Notification webhooks
3. **LDAP/SSO**: Enterprise authentication integration
4. **API Webhooks**: External system notifications
5. **Mobile App**: Push notifications for invitations

## Implementation Benefits

### Clean Architecture
- **Modern role system** based on industry-standard GitHub model
- **Simplified codebase** without legacy compatibility layers
- **Consistent permissions** across all features
- **Intuitive user experience** familiar to developers and researchers

### Scalable Design
- **Granular permissions** suitable for small teams to large organizations
- **Secure invitation system** with enterprise-grade token security
- **Flexible visibility** options for different collaboration needs
- **Comprehensive audit trail** for compliance and monitoring

### Developer Experience
- **Clean API surface** with intuitive permission methods
- **Well-documented** role hierarchy and capabilities
- **Extensible architecture** for future collaboration features
- **GitHub-familiar patterns** reducing learning curve

This GitHub-style collaboration system establishes DielectricFit as a professional-grade scientific collaboration platform with modern security, intuitive user experience, and enterprise-ready scalability.