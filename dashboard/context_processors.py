from django.utils import timezone

from admissions.models import MembershipApplication
from gestion.models import Tarea
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

    # CRM interno: badge de tareas vencidas (solo superadmin ve la sección)
    if request.user.is_superuser:
        context['gestion_vencidas'] = Tarea.objects.exclude(
            estado__in=Tarea.CLOSED_STATES
        ).filter(due_date__lt=timezone.localdate()).count()

    return context
