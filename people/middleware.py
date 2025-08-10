from __future__ import annotations

from django.utils import timezone


class UserTimezoneMiddleware:
    """
    If the user is authenticated and has a profile timezone, copy it into the
    session so Django's TimeZoneMiddleware can activate it consistently.
    Falls back to any session-provided timezone (e.g., set by client detection).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If authenticated and profile has a timezone, ensure it is in the session
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if profile and profile.timezone:
                # Only set if missing or different
                if request.session.get('django_timezone') != profile.timezone:
                    request.session['django_timezone'] = profile.timezone

        # Hand off to the next middleware; django TimeZoneMiddleware will activate
        response = self.get_response(request)
        return response

