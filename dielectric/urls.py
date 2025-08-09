from django.urls import path

from . import views

# App-specific URL patterns
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("analysis/", views.analysis, name="analysis"),
    path("models/", views.models, name="models"),
    path("reports/", views.reports, name="reports"),
    path("preferences/", views.preferences, name="preferences"),
    path("profile/", views.user_profile, name="profile"),

    # API endpoints
    path("api/datasets/", views.datasets_api_list, name="api_datasets_list"),
    path("api/datasets/upload/", views.process_uploaded_dataset, name="api_process_uploaded_dataset"),
    path("api/datasets/create/", views.datasets_api_create, name="api_datasets_create"),
    path("api/datasets/<uuid:dataset_id>/update/", views.datasets_api_update, name="api_datasets_update"),
    path("api/datasets/<uuid:dataset_id>/", views.datasets_api_delete, name="api_datasets_delete"),
    path("api/datasets/<uuid:dataset_id>/data/", views.dataset_data_api, name="api_dataset_data"),
    path("api/datasets/<uuid:dataset_id>/move/", views.move_dataset_api, name="api_move_dataset"),
    
    # Project API endpoints
    path("api/projects/", views.user_projects_api, name="api_user_projects"),
    path("api/projects/switch/", views.switch_active_project_api, name="api_switch_active_project"),
    path("api/projects/create/", views.create_project_api, name="api_create_project"),
    path("api/projects/<uuid:project_id>/delete/", views.delete_project_api, name="api_delete_project"),
]
