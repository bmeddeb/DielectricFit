# Leveraging Django's Permission System for DielectricFit Collaboration

## Overview

Instead of building a custom role system, we can leverage Django's powerful built-in `User`, `Group`, and `Permission` models to create a robust, standardized collaboration system that integrates seamlessly with Django's security framework.

## Architecture Using Django's Native System

### Core Components

1. **Django User Model**: Built-in user authentication
2. **Django Group Model**: Role-based groupings (GitHub-style roles)
3. **Django Permission Model**: Granular permissions on models/actions
4. **Custom Project-specific Groups**: Dynamic groups per project
5. **Permission Decorators**: View-level authorization

## Permission Structure

### Model-Level Permissions

Django automatically creates these permissions for each model:

```python
# Automatically created by Django
'add_dataset'       # Can create new datasets
'change_dataset'    # Can modify existing datasets  
'delete_dataset'    # Can delete datasets
'view_dataset'      # Can view datasets

'add_analysis'      # Can create analyses
'change_analysis'   # Can modify analyses
'delete_analysis'   # Can delete analyses
'view_analysis'     # Can view analyses

'add_project'       # Can create projects
'change_project'    # Can modify project settings
'delete_project'    # Can delete projects
'view_project'      # Can view projects
```

### Custom Permissions

We add GitHub-style permissions to our models:

```python
class Dataset(models.Model):
    # ... existing fields ...
    
    class Meta:
        permissions = [
            # GitHub-style permissions
            ("download_dataset", "Can download dataset files"),
            ("share_dataset", "Can share dataset with others"),
            ("export_dataset", "Can export dataset to external formats"),
            
            # Analysis permissions
            ("run_analysis_on_dataset", "Can run analyses on this dataset"),
            ("publish_dataset", "Can make dataset public"),
            
            # Collaboration permissions  
            ("invite_collaborators_dataset", "Can invite collaborators to dataset"),
            ("manage_dataset_permissions", "Can manage who has access to dataset"),
        ]

class Project(models.Model):
    # ... existing fields ...
    
    class Meta:
        permissions = [
            # Project management
            ("manage_project_settings", "Can manage project settings"),
            ("invite_project_members", "Can invite members to project"),
            ("manage_project_members", "Can add/remove/modify project members"),
            ("archive_project", "Can archive/restore project"),
            
            # Repository-like permissions
            ("create_project_branches", "Can create branches in project"),
            ("merge_project_branches", "Can merge branches in project"),
            ("create_project_releases", "Can create tagged releases"),
            ("manage_project_webhooks", "Can manage project webhooks/integrations"),
            
            # Advanced permissions
            ("transfer_project_ownership", "Can transfer project ownership"),
            ("delete_project_force", "Can force delete project with data"),
        ]

class Analysis(models.Model):
    # ... existing fields ...
    
    class Meta:
        permissions = [
            # Analysis workflow
            ("rerun_analysis", "Can rerun existing analysis"),
            ("clone_analysis", "Can clone analysis to new dataset"),
            ("export_analysis_results", "Can export analysis results"),
            ("publish_analysis", "Can make analysis public"),
            
            # Version control
            ("create_analysis_version", "Can create new analysis versions"),
            ("merge_analysis_versions", "Can merge analysis versions"),
            ("tag_analysis_version", "Can tag analysis versions"),
            
            # Collaboration
            ("review_analysis", "Can review and approve analysis"),
            ("comment_on_analysis", "Can comment on analysis"),
        ]
```

## GitHub-Style Groups Using Django Groups

### Dynamic Project Groups

We create Django Groups dynamically for each project, following GitHub's model:

```python
class ProjectMembershipManager:
    """Manages project memberships using Django's Group system"""
    
    @staticmethod
    def get_project_group_name(project, role):
        """Generate standardized group names"""
        return f"{project.slug}:{role}"
    
    @staticmethod
    def create_project_groups(project):
        """Create all role groups for a project"""
        from django.contrib.auth.models import Group, Permission
        
        roles = {
            'read': [
                'view_project', 'view_dataset', 'view_analysis',
                'download_dataset', 'export_analysis_results'
            ],
            'triage': [
                'view_project', 'view_dataset', 'view_analysis',
                'download_dataset', 'export_analysis_results',
                'comment_on_analysis', 'review_analysis'
            ],
            'write': [
                'view_project', 'view_dataset', 'view_analysis',
                'download_dataset', 'export_analysis_results',
                'add_dataset', 'change_dataset', 'run_analysis_on_dataset',
                'add_analysis', 'change_analysis', 'rerun_analysis',
                'create_analysis_version'
            ],
            'maintain': [
                'view_project', 'view_dataset', 'view_analysis',
                'download_dataset', 'export_analysis_results',
                'add_dataset', 'change_dataset', 'run_analysis_on_dataset',
                'add_analysis', 'change_analysis', 'rerun_analysis',
                'manage_project_settings', 'invite_project_members',
                'create_project_branches', 'create_analysis_version',
                'tag_analysis_version'
            ],
            'admin': [
                'view_project', 'view_dataset', 'view_analysis',
                'download_dataset', 'export_analysis_results',
                'add_dataset', 'change_dataset', 'delete_dataset',
                'add_analysis', 'change_analysis', 'delete_analysis',
                'manage_project_settings', 'invite_project_members',
                'manage_project_members', 'create_project_branches',
                'merge_project_branches', 'create_project_releases',
                'create_analysis_version', 'merge_analysis_versions',
                'tag_analysis_version'
            ],
            'owner': [
                # All permissions - they get everything
                # This would be all permissions for the project
            ]
        }
        
        project_groups = {}
        for role, permission_codenames in roles.items():
            group_name = ProjectMembershipManager.get_project_group_name(project, role)
            group, created = Group.objects.get_or_create(name=group_name)
            
            # Clear existing permissions
            group.permissions.clear()
            
            # Add permissions for this role
            permissions = Permission.objects.filter(codename__in=permission_codenames)
            group.permissions.set(permissions)
            
            project_groups[role] = group
            
        return project_groups
    
    @staticmethod
    def add_user_to_project(user, project, role):
        """Add user to project with specific role"""
        # Remove user from all other roles in this project first
        ProjectMembershipManager.remove_user_from_project(user, project)
        
        # Add to new role group
        group_name = ProjectMembershipManager.get_project_group_name(project, role)
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        
        # Create audit record
        ProjectMembership.objects.create(
            project=project,
            user=user,
            role=role,
            invited_by=None  # Set appropriately
        )
    
    @staticmethod
    def remove_user_from_project(user, project):
        """Remove user from all project groups"""
        project_groups = Group.objects.filter(
            name__startswith=f"{project.slug}:"
        )
        user.groups.remove(*project_groups)
        
        # Remove membership record
        ProjectMembership.objects.filter(
            project=project,
            user=user
        ).delete()
    
    @staticmethod
    def get_user_project_role(user, project):
        """Get user's role in project"""
        user_groups = user.groups.filter(
            name__startswith=f"{project.slug}:"
        ).values_list('name', flat=True)
        
        for group_name in user_groups:
            role = group_name.split(':')[1]
            return role
        
        return None
    
    @staticmethod 
    def user_has_project_permission(user, project, permission):
        """Check if user has specific permission in project"""
        if not user.is_authenticated:
            return False
            
        # Check if user has permission through project groups
        project_groups = user.groups.filter(
            name__startswith=f"{project.slug}:"
        )
        
        return user.has_perm(permission) and project_groups.exists()
```

## Enhanced Models

### Simplified Project Model

```python
class Project(models.Model):
    """Project model leveraging Django's permission system"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)  # Used for group names
    description = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=16, 
        choices=ProjectVisibility.choices, 
        default=ProjectVisibility.PRIVATE
    )
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_projects")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        permissions = [
            ("manage_project_settings", "Can manage project settings"),
            ("invite_project_members", "Can invite members to project"),
            ("manage_project_members", "Can add/remove/modify project members"),
            ("create_project_branches", "Can create branches in project"),
            ("merge_project_branches", "Can merge branches in project"),
            ("transfer_project_ownership", "Can transfer project ownership"),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Create project groups
            ProjectMembershipManager.create_project_groups(self)
            # Add creator as owner
            ProjectMembershipManager.add_user_to_project(self.created_by, self, 'owner')
    
    # Clean permission checking methods
    def user_can_read(self, user):
        return ProjectMembershipManager.user_has_project_permission(
            user, self, 'dielectric.view_project'
        )
    
    def user_can_write(self, user):
        return ProjectMembershipManager.user_has_project_permission(
            user, self, 'dielectric.add_dataset'
        )
    
    def user_can_maintain(self, user):
        return ProjectMembershipManager.user_has_project_permission(
            user, self, 'dielectric.manage_project_settings'
        )
    
    def user_can_admin(self, user):
        return ProjectMembershipManager.user_has_project_permission(
            user, self, 'dielectric.manage_project_members'
        )

class ProjectMembership(models.Model):
    """Audit trail for project memberships (read-only record)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=20, choices=[
        ('read', 'Read'),
        ('triage', 'Triage'), 
        ('write', 'Write'),
        ('maintain', 'Maintain'),
        ('admin', 'Admin'),
        ('owner', 'Owner')
    ])
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    # This model is primarily for audit/history - actual permissions come from Groups
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="uq_project_membership")
        ]
```

## Enhanced Invitation System

### Django Permission-Aware Invitations

```python
class ProjectInvitation(models.Model):
    """Enhanced invitation system using Django permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='invitations')
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invited_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    
    # GitHub-style role that maps to Django Group
    role = models.CharField(max_length=20, choices=[
        ('read', 'Read'),
        ('triage', 'Triage'),
        ('write', 'Write'), 
        ('maintain', 'Maintain'),
        ('admin', 'Admin')
        # Note: 'owner' role typically not available for invitations
    ])
    
    message = models.TextField(blank=True, default="")
    token = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def accept(self, user):
        """Accept invitation and add to appropriate Django Group"""
        if not self.can_accept():
            raise ValidationError("Invitation cannot be accepted")
        
        if self.email.lower() != user.email.lower():
            raise ValidationError("Email mismatch")
        
        # Add user to project with specified role (creates Django Group membership)
        ProjectMembershipManager.add_user_to_project(user, self.project, self.role)
        
        # Mark invitation as accepted
        self.status = ProjectInvitationStatus.ACCEPTED
        self.responded_at = timezone.now()
        self.invited_user = user
        self.save()
```

## View-Level Authorization

### Permission Decorators and Mixins

```python
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied

# Decorator for function-based views
def project_permission_required(permission):
    """Custom decorator for project-specific permissions"""
    def decorator(view_func):
        def wrapped_view(request, project_id=None, *args, **kwargs):
            project = get_object_or_404(Project, id=project_id)
            
            if not ProjectMembershipManager.user_has_project_permission(
                request.user, project, permission
            ):
                raise PermissionDenied(f"You don't have {permission} permission for this project")
            
            return view_func(request, project_id=project_id, *args, **kwargs)
        return wrapped_view
    return decorator

# Usage examples:
@project_permission_required('dielectric.add_dataset')
def upload_dataset(request, project_id):
    """Only users with write access can upload datasets"""
    project = get_object_or_404(Project, id=project_id)
    # ... upload logic ...

@project_permission_required('dielectric.manage_project_members')  
def manage_members(request, project_id):
    """Only admins can manage project members"""
    project = get_object_or_404(Project, id=project_id)
    # ... member management logic ...

# Class-based view mixin
class ProjectPermissionRequiredMixin(PermissionRequiredMixin):
    """Mixin for checking project-specific permissions"""
    project_permission_required = None
    
    def dispatch(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id') or kwargs.get('pk')
        project = get_object_or_404(Project, id=project_id)
        
        if not ProjectMembershipManager.user_has_project_permission(
            request.user, project, self.project_permission_required
        ):
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)

# Usage:
class DatasetCreateView(ProjectPermissionRequiredMixin, CreateView):
    model = Dataset
    project_permission_required = 'dielectric.add_dataset'
    # ... view logic ...
```

## Template Integration

### Permission Checking in Templates

```html
<!-- Check permissions in templates -->
{% load auth_extras %}

<!-- Check if user can upload datasets to this project -->
{% if user|has_project_perm:"dielectric.add_dataset"|project:project %}
    <button onclick="uploadDataset()">Upload Dataset</button>
{% endif %}

<!-- Check if user can manage project settings -->
{% if user|has_project_perm:"dielectric.manage_project_settings"|project:project %}
    <a href="{% url 'project_settings' project.id %}">Project Settings</a>
{% endif %}

<!-- Show different UI based on role -->
{% with role=user|get_project_role:project %}
    {% if role == 'owner' or role == 'admin' %}
        <div class="admin-panel">...</div>
    {% elif role == 'maintain' %}
        <div class="maintainer-panel">...</div>
    {% else %}
        <div class="read-only-panel">...</div>
    {% endif %}
{% endwith %}
```

### Custom Template Tags

```python
# templatetags/auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter
def has_project_perm(user, permission):
    """Check if user has project permission"""
    def check_project(project):
        return ProjectMembershipManager.user_has_project_permission(user, project, permission)
    return check_project

@register.filter  
def get_project_role(user, project):
    """Get user's role in project"""
    return ProjectMembershipManager.get_user_project_role(user, project)

@register.simple_tag
def project_member_count(project, role=None):
    """Count project members by role"""
    if role:
        group_name = ProjectMembershipManager.get_project_group_name(project, role)
        group = Group.objects.get(name=group_name)
        return group.user_set.count()
    else:
        # Count all members
        all_groups = Group.objects.filter(name__startswith=f"{project.slug}:")
        return User.objects.filter(groups__in=all_groups).distinct().count()
```

## Benefits of Django Permission Integration

### 1. **Standardization**
- Uses Django's battle-tested permission system
- Familiar to Django developers
- Follows Django best practices
- Integrates with Django Admin

### 2. **Flexibility** 
- Fine-grained permissions at model level
- Easy to add new permissions
- Role-based access through Groups
- Custom permission logic when needed

### 3. **Performance**
- Efficient database queries
- Built-in caching mechanisms
- Optimized permission checking
- Minimal overhead

### 4. **Security**
- Proven security model
- OWASP compliance
- Audit trail capabilities
- Integration with Django's CSRF/security features

### 5. **Maintainability**
- Less custom code to maintain
- Well-documented Django patterns
- Easy debugging and testing
- Django admin integration for management

### 6. **Ecosystem Integration**
- Works with Django REST Framework permissions
- Compatible with third-party packages
- Easy to extend and customize
- Future-proof with Django updates

## Migration Strategy

### From Custom Roles to Django Groups

```python
class MigrateToDjangoPermissions:
    """Migration utility to convert custom roles to Django Groups"""
    
    @staticmethod
    def migrate_existing_memberships():
        """Convert existing ProjectMembership records to Django Groups"""
        from django.contrib.auth.models import Group
        
        # Create groups for all projects
        for project in Project.objects.all():
            ProjectMembershipManager.create_project_groups(project)
        
        # Migrate existing memberships
        for membership in ProjectMembership.objects.all():
            # Map legacy roles to new roles
            role_mapping = {
                'member': 'write',
                'viewer': 'read',
                'admin': 'admin',
                'owner': 'owner'
            }
            
            new_role = role_mapping.get(membership.role, membership.role)
            
            # Add user to appropriate group
            ProjectMembershipManager.add_user_to_project(
                membership.user, 
                membership.project, 
                new_role
            )
```

This Django permission integration provides a **robust, standardized, and scalable** approach to project collaboration that leverages Django's proven security framework while maintaining the GitHub-style user experience we want for DielectricFit! 🚀

<system-reminder>
Background Bash bash_1 (command: python manage.py runserver) (status: running) Has new output available. You can check its output using the BashOutput tool.
</system-reminder></function_results>

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Research GitHub's project/repository membership architecture", "status": "completed", "id": "1"}, {"content": "Design enhanced membership system with invitations", "status": "completed", "id": "2"}, {"content": "Implement GitHub-like collaboration features", "status": "completed", "id": "3"}, {"content": "Create invitation API views and templates", "status": "pending", "id": "4"}, {"content": "Update frontend to support new role system", "status": "pending", "id": "5"}, {"content": "Document GitHub-style collaboration system", "status": "completed", "id": "6"}, {"content": "Design Git-like versioning system for analyses and reports", "status": "completed", "id": "7"}, {"content": "Evaluate Django's built-in permissions system integration", "status": "completed", "id": "8"}]