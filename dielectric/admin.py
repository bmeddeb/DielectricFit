from django.contrib import admin

from .models import (
    Dataset, RawDataPoint, Project, ProjectMembership, ProjectActivity
)


class RawDataPointInline(admin.TabularInline):
    model = RawDataPoint
    extra = 0
    readonly_fields = ('point_index', 'frequency_hz', 'dk', 'df', 'epsilon_real', 'epsilon_imag')
    can_delete = False
    max_num = 10  # Show first 10 points for a quick preview


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 0
    readonly_fields = ('joined_at', 'last_accessed_at', 'access_count')


class DatasetInline(admin.TabularInline):
    model = Dataset
    extra = 0
    readonly_fields = ('id', 'owner', 'name', 'row_count', 'created_at')
    fields = ('name', 'owner', 'row_count', 'status', 'created_at')
    can_delete = False
    max_num = 10


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "visibility", "dataset_count", "total_data_points", "last_activity_at", "created_at")
    search_fields = ("name", "created_by__username", "description")
    list_filter = ("visibility", "created_at", "last_activity_at")
    readonly_fields = ('id', 'created_at', 'updated_at', 'dataset_count', 'total_data_points', 'last_activity_at')
    inlines = [ProjectMembershipInline, DatasetInline]
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'visibility', 'created_by')
        }),
        ('Metadata', {
            'fields': ('dataset_count', 'total_data_points', 'last_activity_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at', 'archived_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "role", "joined_at", "last_accessed_at", "access_count")
    search_fields = ("user__username", "project__name")
    list_filter = ("role", "joined_at")
    readonly_fields = ('id', 'joined_at', 'updated_at', 'last_accessed_at', 'access_count')


@admin.register(ProjectActivity)
class ProjectActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "project", "action", "created_at")
    search_fields = ("user__username", "project__name", "action", "description")
    list_filter = ("action", "created_at")
    readonly_fields = ('id', 'created_at')


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "project", "owner", "status", "row_count", "created_at")
    search_fields = ("name", "owner__username", "project__name")
    list_filter = ("status", "input_schema", "project")
    readonly_fields = ('id', 'created_at', 'updated_at', 'ingest_fingerprint')
    inlines = [RawDataPointInline]


@admin.register(RawDataPoint)
class RawDataPointAdmin(admin.ModelAdmin):
    list_display = ('dataset', 'point_index', 'frequency_hz', 'dk', 'df', 'epsilon_real', 'epsilon_imag')
    search_fields = ('dataset__name',)
    list_per_page = 25
