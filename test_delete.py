#!/usr/bin/env python
import os
import django
import sys

# Add the project root to the Python path
sys.path.insert(0, '/Users/ben/django_projects/DielectricFit')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from people.models import Project
from dielectric.models import Dataset

User = get_user_model()

# Get a test user
user = User.objects.first()
if not user:
    print("No users found")
    sys.exit(1)

print(f"Testing with user: {user.username}")

# Find a non-default project
projects = Project.objects.filter(
    memberships__user=user,
    memberships__role="owner"
).exclude(name="Default")

if not projects.exists():
    print("No non-default projects found for this user")
    sys.exit(1)

project = projects.first()
print(f"Testing deletion of project: {project.name} (id: {project.id})")

# Check if project has datasets
datasets = Dataset.objects.filter(project=project)
print(f"Project has {datasets.count()} datasets")

# Try to execute the delete logic
try:
    from django.db import transaction, IntegrityError
    from people.models import ProjectMembership, UserProjectPreference
    
    # Get or create default project
    default_project, _created = Project.objects.get_or_create(
        name="Default",
        created_by=user,
        defaults={
            "description": "Default project for your datasets",
            "visibility": "private"
        }
    )
    
    if _created:
        ProjectMembership.objects.create(
            project=default_project,
            user=user,
            role="owner"
        )
    
    print(f"Default project: {default_project.name} (id: {default_project.id})")
    
    # Move datasets
    print("Moving datasets...")
    with transaction.atomic():
        for ds in datasets:
            try:
                print(f"  Moving dataset: {ds.name}")
                ds.project = default_project
                ds.save(update_fields=["project", "updated_at"])
                print(f"    Moved successfully")
            except IntegrityError as e:
                print(f"    IntegrityError: {e}")
                # Try with fingerprint cleared
                if ds.ingest_fingerprint:
                    ds.ingest_fingerprint = None
                if ds.name and not ds.name.endswith(f"-{project.name}"):
                    ds.name = f"{ds.name}-{project.name}"
                ds.project = default_project
                ds.save(update_fields=["project", "updated_at", "ingest_fingerprint", "name"])
                print(f"    Moved with modifications")
    
    # Update metadata
    print("Updating metadata...")
    default_project.update_metadata()
    default_project.update_activity()
    
    print("Success! Datasets moved successfully")
    
except Exception as e:
    import traceback
    print(f"Error: {e}")
    print("Traceback:")
    traceback.print_exc()