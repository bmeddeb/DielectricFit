from django.contrib import admin
from .models import Project, ProjectMembership, ProjectActivity, UserProfile


@admin.register(UserProfile) 
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'timezone', 'email_notifications', 'created_at')
    search_fields = ('user__username', 'user__email')
    list_filter = ('timezone', 'email_notifications', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
