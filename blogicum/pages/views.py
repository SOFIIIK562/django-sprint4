"""Render static information pages."""
from django.shortcuts import render


def csrf_failure(request, reason=''):
    """Render a CSRF failure without exposing technical details."""
    return render(request, 'pages/403csrf.html', status=403)


def page_not_found(request, exception):
    """Render a missing-page response with the correct status."""
    return render(request, 'pages/404.html', status=404)


def server_error(request):
    """Render the generic server failure page."""
    return render(request, 'pages/500.html', status=500)
