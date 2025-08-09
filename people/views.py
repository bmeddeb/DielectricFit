from __future__ import annotations

import logging
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Project, ProjectMembership, UserProjectPreference, ProjectActivity, ProjectVisibility
from .forms import CustomUserCreationForm
from dielectric.models import Dataset

# Set up logger
logger = logging.getLogger(__name__)


def register(request: HttpRequest) -> HttpResponse:
    """User registration view"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            logger.info(f"New user registered: {user.username}")
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def get_or_create_active_project(user):
    """Get user's active project or create a default one"""
    if not user.is_authenticated:
        return None
        
    # Get user's preference
    preference, created = UserProjectPreference.objects.get_or_create(user=user)
    
    # Check if current active project is still valid
    if preference.active_project:
        try:
            # Verify the project still exists and user has access
            if preference.active_project.user_can_view(user):
                return preference.active_project
        except Project.DoesNotExist:
            # Project was deleted, clear the preference
            preference.active_project = None
            preference.save()
    
    # Find user's projects (refresh the list)
    user_projects = Project.objects.filter(memberships__user=user).order_by('-last_activity_at')
    
    if user_projects.exists():
        # Set first project as active
        preference.active_project = user_projects.first()
        preference.save()
        return preference.active_project
    
    # No projects found - get or create a Default project
    logger.info(f"Getting or creating Default project for user {user.username}")
    default_project, created = Project.objects.get_or_create(
        name="Default",
        created_by=user,
        defaults={
            "description": "Default project for your datasets",
            "visibility": "private"
        }
    )
    
    # Ensure user has owner membership (in case project existed but membership didn't)
    membership, membership_created = ProjectMembership.objects.get_or_create(
        project=default_project,
        user=user,
        defaults={"role": "owner"}
    )
    
    if created:
        logger.info(f"Created new Default project for user {user.username}")
    elif membership_created:
        logger.info(f"Added missing membership to existing Default project for user {user.username}")
    
    # Set as active
    preference.active_project = default_project
    preference.save()
    
    return default_project


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    return render(request, "people/profile.html")


@login_required
@require_http_methods(["GET"])
def user_projects_api(request: HttpRequest) -> JsonResponse:
    """Return user's accessible projects for project switcher"""
    try:
        # Ensure user has at least one project
        user_projects = Project.objects.filter(
            memberships__user=request.user
        ).annotate(
            member_count=Count('memberships')
        ).order_by('-last_activity_at')
        
        # If user has no projects, create a default one
        if not user_projects.exists():
            active_project = get_or_create_active_project(request.user)
            user_projects = Project.objects.filter(
                memberships__user=request.user
            ).annotate(
                member_count=Count('memberships')
            ).order_by('-last_activity_at')
        
        # Get user's current active project
        active_project_id = None
        try:
            preference = UserProjectPreference.objects.get(user=request.user)
            active_project_id = str(preference.active_project.id) if preference.active_project else None
        except UserProjectPreference.DoesNotExist:
            pass
        
        projects_data = []
        for project in user_projects:
            project_data = {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "dataset_count": project.dataset_count,
                "member_count": project.member_count,
                "is_active": str(project.id) == active_project_id,
                "last_activity": project.last_activity_at.isoformat(),
                "visibility": project.visibility
            }
            projects_data.append(project_data)
        
        return JsonResponse({
            "ok": True,
            "projects": projects_data,
            "count": len(projects_data)
        })
        
    except Exception as e:
        import traceback
        logger.error(f"Error in user_projects_api: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({
            "ok": False,
            "error": str(e),
            "projects": []
        }, status=500)


@login_required
@require_http_methods(["POST"])
def switch_active_project_api(request: HttpRequest) -> JsonResponse:
    """Switch user's active project"""
    import json
    
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        
        if not project_id:
            return JsonResponse({"ok": False, "error": "Project ID required"}, status=400)
        
        # Verify user has access to this project
        project = get_object_or_404(Project, id=project_id, memberships__user=request.user)
        
        # Update user's active project preference
        preference, created = UserProjectPreference.objects.get_or_create(user=request.user)
        preference.active_project = project
        preference.save()
        
        # Track project access
        membership = project.get_user_membership(request.user)
        if membership:
            membership.track_access()
        
        return JsonResponse({
            "ok": True,
            "active_project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "dataset_count": project.dataset_count
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Project.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Project not found or access denied"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def create_project_api(request: HttpRequest) -> JsonResponse:
    """Create a new project"""
    import json
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        visibility = data.get('visibility', 'private')
        
        if not name:
            return JsonResponse({"ok": False, "error": "Project name is required"}, status=400)
        
        if visibility not in ['private', 'internal', 'public']:
            return JsonResponse({"ok": False, "error": "Invalid visibility option"}, status=400)
        
        # Create project
        project = Project.objects.create(
            name=name,
            description=description,
            visibility=visibility,
            created_by=request.user
        )
        
        # Create owner membership
        ProjectMembership.objects.create(
            project=project,
            user=request.user,
            role="owner"
        )
        
        # Set as active project
        preference, created = UserProjectPreference.objects.get_or_create(user=request.user)
        preference.active_project = project
        preference.save()
        
        return JsonResponse({
            "ok": True,
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "visibility": project.visibility
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_project_api(request: HttpRequest, project_id) -> JsonResponse:
    """Delete a project and all its datasets"""
    try:
        # Get project and verify user is owner
        project = get_object_or_404(
            Project, 
            id=project_id, 
            memberships__user=request.user,
            memberships__role="owner"
        )
        
        # Prevent deletion of default project
        if project.name == "Default":
            return JsonResponse({"ok": False, "error": "Cannot delete the default project"}, status=400)
        
        # If this was the user's active project, switch to another project
        try:
            preference = UserProjectPreference.objects.get(user=request.user)
            if preference.active_project == project:
                # Find another project for the user
                other_project = Project.objects.filter(
                    memberships__user=request.user
                ).exclude(id=project.id).first()
                
                if other_project:
                    preference.active_project = other_project
                    preference.save()
                else:
                    # Create a new default project
                    default_project = Project.objects.create(
                        name="Default",
                        description="Default project for your datasets",
                        visibility="private",
                        created_by=request.user
                    )
                    ProjectMembership.objects.create(
                        project=default_project,
                        user=request.user,
                        role="owner"
                    )
                    preference.active_project = default_project
                    preference.save()
        except UserProjectPreference.DoesNotExist:
            pass
        
        # Before deleting, move datasets to user's Default project (in a transaction)
        default_project, _created = Project.objects.get_or_create(
            name="Default",
            created_by=request.user,
            defaults={
                "description": "Default project for your datasets",
                "visibility": "private"
            }
        )

        # Ensure user has owner membership on Default project
        if _created:
            ProjectMembership.objects.create(
                project=default_project,
                user=request.user,
                role="owner"
            )

        if default_project.id == project.id:
            # If attempting to delete the default project, block (handled above), but double-check
            return JsonResponse({"ok": False, "error": "Cannot delete the default project"}, status=400)

        # Move datasets; handle potential fingerprint uniqueness conflicts by dropping duplicates
        datasets = Dataset.objects.filter(project=project).order_by('created_at')
        with transaction.atomic():
            for ds in datasets:
                try:
                    ds.project = default_project
                    ds.save(update_fields=["project", "updated_at"])  # triggers project metadata updates
                except IntegrityError:
                    # Conflict on (project, ingest_fingerprint). Preserve both by clearing fingerprint
                    # and appending source project name to dataset name to indicate provenance.
                    try:
                        if ds.ingest_fingerprint:
                            ds.ingest_fingerprint = None
                        # Append suffix once
                        if ds.name and not ds.name.endswith(f"-{project.name}"):
                            ds.name = f"{ds.name}-{project.name}"
                        ds.project = default_project
                        ds.save(update_fields=["project", "updated_at", "ingest_fingerprint", "name"])  # retry
                    except IntegrityError:
                        # As a last resort, drop the dataset to unblock deletion
                        ds.delete()

        # After moving, update metadata on both projects just in case
        default_project.update_metadata()
        default_project.update_activity()
        project_name = project.name
        project.delete()

        return JsonResponse({"ok": True, "message": f"Project '{project_name}' deleted successfully"})
        
    except Project.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Project not found or you don't have permission to delete it"}, status=404)
    except Exception as e:
        import traceback
        logger.error(f"Error deleting project {project_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_project_api(request: HttpRequest, project_id) -> JsonResponse:
    """Update project details"""
    import json
    
    try:
        data = json.loads(request.body)
        
        # Get project and verify user is owner or admin
        project = get_object_or_404(
            Project, 
            id=project_id, 
            memberships__user=request.user,
            memberships__role__in=["owner", "admin"]
        )
        
        # Update fields
        if 'name' in data:
            project.name = data['name'].strip()
        if 'description' in data:
            project.description = data['description'].strip()
        if 'visibility' in data and data['visibility'] in ['private', 'internal', 'public']:
            project.visibility = data['visibility']
        
        project.save()
        
        return JsonResponse({
            "ok": True,
            "message": "Project updated successfully",
            "project": {
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "visibility": project.visibility
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Project.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Project not found or access denied"}, status=404)
    except Exception as e:
        logger.error(f"Error updating project: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def update_profile_api(request: HttpRequest) -> JsonResponse:
    """Update user profile information"""
    import json
    
    try:
        data = json.loads(request.body)
        user = request.user
        
        # Update user fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'email' in data:
            # Basic email validation
            email = data['email'].strip()
            if '@' in email and '.' in email:
                user.email = email
            else:
                return JsonResponse({"ok": False, "error": "Invalid email format"}, status=400)
        
        user.save()
        
        # Handle additional profile fields (phone, timezone) if we have a profile model
        # For now, we'll just return success
        
        return JsonResponse({
            "ok": True,
            "message": "Profile updated successfully"
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def profile_projects_api(request: HttpRequest) -> JsonResponse:
    """Get all projects with datasets for profile page"""
    try:
        # Get all user's projects with their datasets
        projects = Project.objects.filter(
            memberships__user=request.user
        ).prefetch_related(
            'datasets', 
            'memberships'
        ).annotate(
            total_datasets=Count('datasets', distinct=True),
            total_members=Count('memberships', distinct=True)
        ).order_by('-created_at')
        
        projects_data = []
        for project in projects:
            # Get active project info
            active_project = None
            try:
                user_pref = UserProjectPreference.objects.get(user=request.user)
                active_project = user_pref.active_project
            except UserProjectPreference.DoesNotExist:
                pass
            
            # Get recent datasets - import Dataset here to avoid circular imports
            from dielectric.models import Dataset
            recent_datasets = Dataset.objects.filter(project=project).order_by('-created_at')[:10]
            datasets_data = []
            
            for dataset in recent_datasets:
                datasets_data.append({
                    "id": str(dataset.id),
                    "name": dataset.name,
                    "created_at": dataset.created_at.strftime("%b %d, %Y"),
                    "row_count": dataset.row_count,
                    "description": dataset.description
                })
            
            projects_data.append({
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "visibility": project.visibility,
                "created_at": project.created_at.strftime("%b %d, %Y"),
                "dataset_count": project.total_datasets,
                "member_count": project.total_members,
                "is_active": active_project and active_project.id == project.id,
                "datasets": datasets_data
            })
        
        return JsonResponse({
            "ok": True,
            "projects": projects_data
        })
        
    except Exception as e:
        logger.error(f"Error getting profile projects: {e}")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
