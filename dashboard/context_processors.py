from admissions.models import MembershipApplication
from users.models import User


def dashboard_context(request):
    """Context processor for dashboard sidebar data."""
    if not request.user.is_authenticated:
        return {}

    if not (request.user.is_staff or request.user.is_superuser):
        return {}

    # Only run on dashboard paths
    if not request.path.startswith('/portal/'):
        return {}

    context = {
        'pending_count': MembershipApplication.objects.filter(
            status=MembershipApplication.Status.PENDING
        ).count(),
        'sidebar_users': User.objects.filter(
            is_staff=True
        ).order_by('first_name', 'last_name'),
    }

    return context
