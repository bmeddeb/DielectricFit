from django.urls import path
from . import views

app_name = 'people'

urlpatterns = [
    # Auth views
    path('register/', views.register, name='register'),
    
    # Profile views
    path('profile/', views.user_profile, name='profile'),
    
    # Profile API endpoints
    path('api/profile/update/', views.update_profile_api, name='api_update_profile'),
    path('api/profile/projects/', views.profile_projects_api, name='api_profile_projects'),
    path('api/timezone/set/', views.set_timezone_api, name='api_set_timezone'),
    
    # Project API endpoints
    path('api/projects/', views.user_projects_api, name='api_user_projects'),
    path('api/projects/switch/', views.switch_active_project_api, name='api_switch_active_project'),
    path('api/projects/create/', views.create_project_api, name='api_create_project'),
    path('api/projects/<uuid:project_id>/update/', views.update_project_api, name='api_update_project'),
    path('api/projects/<uuid:project_id>/delete/', views.delete_project_api, name='api_delete_project'),
]
