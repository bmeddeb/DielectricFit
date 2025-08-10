from __future__ import annotations

from django.utils import timezone
import zoneinfo


class UserTimezoneMiddleware:
    """
    If the user is authenticated and has a profile timezone, copy it into the
    session so Django's TimeZoneMiddleware can activate it consistently.
    Falls back to any session-provided timezone (e.g., set by client detection).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Determine desired timezone: user profile first, then session, else None
        tzname = None
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            if profile and profile.timezone:
                tzname = profile.timezone
                # Keep session in sync for client-side use
                if request.session.get('django_timezone') != tzname:
                    request.session['django_timezone'] = tzname
        if not tzname:
            tzname = request.session.get('django_timezone')

        # Activate/deactivate timezone for this request
        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except Exception:
                timezone.deactivate()
        else:
            timezone.deactivate()

        response = self.get_response(request)
        return response
