from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"
    verbose_name = "Model/Algorithm Library"

    def ready(self) -> None:  # pragma: no cover - import-time registration
        # Import dielectric models to populate the registry at app startup
        try:
            from .dielectric.models import debye, cole_cole  # noqa: F401
        except Exception:  # Keep app startup resilient
            # If optional dependencies or numerical backends are missing, avoid crashing.
            pass
