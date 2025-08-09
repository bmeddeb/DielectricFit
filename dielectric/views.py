from __future__ import annotations

import hashlib
import io
import re
import pandas as pd
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .models import Dataset, RawDataPoint, InputSchema, Analysis, FittingSession, Project, ProjectMembership, UserProjectPreference, ProjectActivity


def get_or_create_active_project(user):
    """Get user's active project or create a default one"""
    if not user.is_authenticated:
        return None
        
    # Get user's preference
    preference, created = UserProjectPreference.objects.get_or_create(user=user)
    
    if preference.active_project and preference.active_project.user_can_view(user):
        return preference.active_project
    
    # Find user's projects
    user_projects = Project.objects.filter(memberships__user=user).order_by('-last_activity_at')
    
    if user_projects.exists():
        # Set first project as active
        preference.active_project = user_projects.first()
        preference.save()
        return preference.active_project
    
    # Create default project if user has none
    default_project = Project.objects.create(
        name="Default",
        description="Default project for your datasets",
        visibility="private",
        created_by=user
    )
    
    # Create owner membership
    ProjectMembership.objects.create(
        project=default_project,
        user=user,
        role="owner"
    )
    
    # Set as active
    preference.active_project = default_project
    preference.save()
    
    return default_project


def dashboard(request: HttpRequest) -> HttpResponse:
    # Get user's accessible projects and datasets
    if request.user.is_authenticated:
        # Get user's active project
        active_project = get_or_create_active_project(request.user)
        
        # Get projects user has access to
        user_projects = Project.objects.filter(
            memberships__user=request.user
        ).distinct().order_by('-last_activity_at')
        
        # Get datasets from active project only (not all accessible projects)
        if active_project:
            datasets = Dataset.objects.filter(
                project=active_project
            ).select_related('project', 'owner').order_by('-created_at')[:24]
        else:
            # Fallback to all accessible datasets if no active project
            datasets = Dataset.objects.filter(
                project__memberships__user=request.user
            ).select_related('project', 'owner').order_by('-created_at')[:24]
        
        # Get analyses from accessible datasets
        analyses = Analysis.objects.filter(
            preprocessing_config__dataset__project__memberships__user=request.user
        ).select_related(
            'preprocessing_config__dataset__project', 
            'preprocessing_config__dataset__owner'
        ).order_by('-created_at')[:12]
        
        # Calculate statistics for active project (or all accessible if no active project)
        if active_project:
            total_datasets = Dataset.objects.filter(project=active_project).count()
            total_analyses = Analysis.objects.filter(
                preprocessing_config__dataset__project=active_project
            ).count()
            today_count = Dataset.objects.filter(
                project=active_project,
                created_at__date=timezone.now().date()
            ).count()
        else:
            # Fallback to all accessible data
            total_datasets = Dataset.objects.filter(
                project__memberships__user=request.user
            ).count()
            total_analyses = Analysis.objects.filter(
                preprocessing_config__dataset__project__memberships__user=request.user
            ).count()
            today_count = Dataset.objects.filter(
                project__memberships__user=request.user,
                created_at__date=timezone.now().date()
            ).count()
        
        # Track access for user's project memberships
        for membership in ProjectMembership.objects.filter(user=request.user):
            membership.track_access()
            
    else:
        # For anonymous users, show public projects only
        active_project = None
        user_projects = Project.objects.filter(
            visibility=Project.ProjectVisibility.PUBLIC
        ).order_by('-last_activity_at')[:10]
        
        datasets = Dataset.objects.filter(
            project__visibility=Project.ProjectVisibility.PUBLIC
        ).select_related('project', 'owner').order_by('-created_at')[:24]
        
        analyses = Analysis.objects.filter(
            preprocessing_config__dataset__project__visibility=Project.ProjectVisibility.PUBLIC
        ).select_related(
            'preprocessing_config__dataset__project', 
            'preprocessing_config__dataset__owner'
        ).order_by('-created_at')[:12]
        
        total_datasets = Dataset.objects.filter(
            project__visibility=Project.ProjectVisibility.PUBLIC
        ).count()
        total_analyses = Analysis.objects.filter(
            preprocessing_config__dataset__project__visibility=Project.ProjectVisibility.PUBLIC
        ).count()
        today_count = Dataset.objects.filter(
            project__visibility=Project.ProjectVisibility.PUBLIC,
            created_at__date=timezone.now().date()
        ).count()
    
    context = {
        'datasets': datasets,
        'analyses': analyses,
        'projects': user_projects if request.user.is_authenticated else [],
        'active_project': active_project,
        'total_datasets': total_datasets,
        'total_analyses': total_analyses,
        'today_count': today_count,
    }
    
    return render(request, "dielectric/dashboard_clean.html", context)

def analysis(request: HttpRequest) -> HttpResponse:
    return render(request, "dielectric/analysis.html")

def models(request: HttpRequest) -> HttpResponse:
    return render(request, "dielectric/models.html")

def reports(request: HttpRequest) -> HttpResponse:
    return render(request, "dielectric/reports.html")

def preferences(request: HttpRequest) -> HttpResponse:
    return render(request, "dielectric/preferences.html")


@login_required
def user_profile(request: HttpRequest) -> HttpResponse:
    return render(request, "dielectric/profile.html")


# --- API Views ---

@login_required
@require_http_methods(["POST"])
@transaction.atomic
def process_uploaded_dataset(request: HttpRequest) -> JsonResponse:
    """
    Handles the upload, parsing, cleaning, and storage of a new dataset from a CSV file.
    """
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"ok": False, "error": "No file provided."}, status=400)

    try:
        file_content = uploaded_file.read()
        fingerprint = hashlib.md5(file_content).hexdigest()

        # Check for duplicates within the active project only (not globally by user)
        active_project = get_or_create_active_project(request.user)
        if Dataset.objects.filter(project=active_project, ingest_fingerprint=fingerprint).exists():
            return JsonResponse({"ok": False, "error": f"This file has already been uploaded to project '{active_project.name}'."}, status=409)

        df = pd.read_csv(io.BytesIO(file_content), comment="#")
        column_map = {col.lower().strip(): col for col in df.columns}

        def find_col(patterns):
            for p in patterns:
                for k, v in column_map.items():
                    if re.search(p, k):
                        return v
            return None

        freq_col = find_col(["freq", "frequency"])
        dk_col = find_col(["dk", "dielectric constant"])
        df_col = find_col(["df", "dissipation factor", "tan"])
        eps_r_col = find_col(["eps_r", "epsilon_r", "eps'", "ε′"])
        eps_i_col = find_col(["eps_i", "epsilon_i", "eps''", "ε″"])

        if not freq_col or not ((dk_col and df_col) or (eps_r_col and eps_i_col)):
            return JsonResponse({"ok": False, "error": "Could not find required columns (freq, and dk/df or ε'/ε″)."}, status=400)

        unit_match = re.search(r'\(?(ghz|mhz|khz|hz)\)?', freq_col, re.IGNORECASE)
        unit = unit_match.group(1).lower() if unit_match else "hz"
        multiplier = {"ghz": 1e9, "mhz": 1e6, "khz": 1e3, "hz": 1}.get(unit, 1)

        df.dropna(how='all', inplace=True)
        input_schema = InputSchema.DK_DF if dk_col else InputSchema.EPS
        
        if input_schema == InputSchema.DK_DF:
            required_cols, rename_map = [freq_col, dk_col, df_col], {freq_col: 'frequency_hz', dk_col: 'dk', df_col: 'df'}
        else:
            required_cols, rename_map = [freq_col, eps_r_col, eps_i_col], {freq_col: 'frequency_hz', eps_r_col: 'epsilon_real', eps_i_col: 'epsilon_imag'}

        df = df[required_cols].rename(columns=rename_map)
        df.dropna(subset=rename_map.values(), inplace=True)
        df['frequency_hz'] = pd.to_numeric(df['frequency_hz']) * multiplier
        df.drop_duplicates(subset=['frequency_hz'], inplace=True)
        df.sort_values('frequency_hz', inplace=True)

        if df.empty:
            return JsonResponse({"ok": False, "error": "No valid data rows found after cleaning."}, status=400)

        # active_project already retrieved above for duplicate check
        
        dataset = Dataset.objects.create(
            project=active_project,
            owner=request.user, 
            name=uploaded_file.name, 
            input_schema=input_schema,
            input_freq_unit=unit, 
            ingest_fingerprint=fingerprint, 
            row_count=len(df), 
            status="uploaded"
        )

        raw_points = [RawDataPoint(dataset=dataset, point_index=i, **row) for i, row in enumerate(df.to_dict('records'))]
        RawDataPoint.objects.bulk_create(raw_points)

        return JsonResponse({
            "ok": True, "dataset_id": dataset.id,
            "summary": {
                "name": dataset.name, "row_count": dataset.row_count,
                "f_min_hz": df['frequency_hz'].min(), "f_max_hz": df['frequency_hz'].max(),
                "unit_detected": unit, "schema_detected": input_schema, "fingerprint": fingerprint,
            },
            "dataset": {
                "id": str(dataset.id),
                "name": dataset.name,
                "row_count": dataset.row_count,
                "input_schema": dataset.input_schema,
                "frequency_unit": dataset.input_freq_unit,
                "frequency_min": float(df['frequency_hz'].min()),
                "frequency_max": float(df['frequency_hz'].max()),
                "created_at": dataset.created_at.isoformat(),
            }
        })
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"An unexpected error occurred: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def datasets_api_list(request: HttpRequest) -> JsonResponse:
    datasets = Dataset.objects.filter(owner=request.user).order_by("-updated_at")
    return JsonResponse({
        "items": [
            {"id": d.id, "name": d.name, "created_at": d.created_at.isoformat(), "updated_at": d.updated_at.isoformat()}
            for d in datasets
        ]
    })


@login_required
@require_http_methods(["POST"])
def datasets_api_create(request: HttpRequest) -> JsonResponse:
    # This is now a simpler version, perhaps for creating a dataset manually without a file.
    name = request.POST.get("name", "Untitled")
    dataset = Dataset.objects.create(owner=request.user, name=name, status="manual")
    return JsonResponse({"id": dataset.id, "ok": True})


@login_required
@require_http_methods(["POST"])
def datasets_api_update(request: HttpRequest, dataset_id: int) -> JsonResponse:
    dataset = get_object_or_404(Dataset, id=dataset_id, owner=request.user)
    if request.POST.get("name"):
        dataset.name = request.POST["name"]
    dataset.save()
    return JsonResponse({"ok": True})


@login_required
@require_http_methods(["DELETE"])
def datasets_api_delete(request: HttpRequest, dataset_id) -> JsonResponse:
    dataset = get_object_or_404(Dataset, id=dataset_id)
    dataset.delete()
    return JsonResponse({"ok": True})


@login_required
def dataset_data_api(request: HttpRequest, dataset_id) -> JsonResponse:
    """Return dataset points for plotting"""
    dataset = get_object_or_404(Dataset, id=dataset_id)
    
    # Get raw data points ordered by frequency
    points = RawDataPoint.objects.filter(dataset=dataset).order_by('frequency_hz')
    
    # Prepare data for plotting
    frequencies = []
    dk_values = []
    df_values = []
    
    for point in points[:100]:  # Limit to 100 points for mini plots
        frequencies.append(float(point.frequency_hz))
        if dataset.input_schema == InputSchema.DK_DF:
            dk_values.append(float(point.dk))
            df_values.append(float(point.df))
        else:  # EPSILON_REAL_IMAG
            # For epsilon data, we'll show real and imaginary parts
            dk_values.append(float(point.epsilon_real))  # epsilon real
            df_values.append(float(point.epsilon_imag))  # epsilon imag
    
    return JsonResponse({
        "frequencies": frequencies,
        "dk": dk_values,
        "df": df_values,
        "schema": dataset.input_schema,
        "frequency_unit": dataset.input_freq_unit
    })


@login_required
@require_http_methods(["GET"])
def user_projects_api(request: HttpRequest) -> JsonResponse:
    """Return user's accessible projects for project switcher"""
    print(f"DEBUG: API called by user: {request.user}")
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
        print(f"DEBUG: Processing {user_projects.count()} projects")
        for project in user_projects:
            print(f"DEBUG: Processing project {project.name}")
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
        
        print(f"DEBUG: Returning {len(projects_data)} projects")
        return JsonResponse({
            "ok": True,
            "projects": projects_data,
            "count": len(projects_data)
        })
        
    except Exception as e:
        import traceback
        print(f"Error in user_projects_api: {str(e)}")
        print(traceback.format_exc())
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
@require_http_methods(["POST"])
def move_dataset_api(request: HttpRequest, dataset_id) -> JsonResponse:
    """Move a dataset to a different project"""
    import json
    
    try:
        # Parse request body
        data = json.loads(request.body)
        target_project_id = data.get("target_project_id")
        
        if not target_project_id:
            return JsonResponse({"ok": False, "error": "Target project ID required"}, status=400)
        
        # Get the dataset and verify ownership
        dataset = get_object_or_404(Dataset, id=dataset_id, owner=request.user)
        
        # Get the target project and verify membership
        target_project = get_object_or_404(
            Project,
            id=target_project_id,
            memberships__user=request.user
        )
        
        # Store old project for audit trail
        old_project = dataset.project
        
        # Move the dataset
        dataset.project = target_project
        dataset.save()
        
        # Create audit trail entries
        # Log in the source project
        ProjectActivity.objects.create(
            project=old_project,
            user=request.user,
            action="dataset_move_out",
            description=f"Moved dataset '{dataset.name}' to project '{target_project.name}'",
            metadata={
                "dataset_id": str(dataset.id),
                "dataset_name": dataset.name,
                "target_project_id": str(target_project.id),
                "target_project_name": target_project.name
            }
        )
        
        # Log in the target project
        ProjectActivity.objects.create(
            project=target_project,
            user=request.user,
            action="dataset_move_in",
            description=f"Received dataset '{dataset.name}' from project '{old_project.name}'",
            metadata={
                "dataset_id": str(dataset.id),
                "dataset_name": dataset.name,
                "source_project_id": str(old_project.id),
                "source_project_name": old_project.name
            }
        )
        
        logger.info(f"User {request.user.username} moved dataset {dataset.name} from project {old_project.name} to {target_project.name}")
        
        return JsonResponse({
            "ok": True,
            "message": f"Dataset moved to {target_project.name}",
            "dataset_id": str(dataset.id),
            "new_project_id": str(target_project.id),
            "new_project_name": target_project.name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"Error moving dataset: {e}")
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
        
        # Delete the project (this will cascade delete datasets and related data)
        project_name = project.name
        project.delete()
        
        return JsonResponse({"ok": True, "message": f"Project '{project_name}' deleted successfully"})
        
    except Project.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Project not found or you don't have permission to delete it"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
