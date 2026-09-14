from visitors.models import Visitor
from lostfound.models import LostFoundItem
from gatepass.models import GatePass
from django.utils import timezone

def security_context(request):
    if not request.user.is_authenticated:
        return {}
    
    now = timezone.now()

    # Active on-premises visitors count
    active_visitors_count = Visitor.objects.filter(status='active').count()
    unclaimed_lf_count = LostFoundItem.objects.filter(status='unclaimed').count()
    
    # Overstaying visitors
    overstay_count = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    ).count()

    # Gate Pass Telemetry
    active_greencards_count = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned']
    ).count()

    overdue_greencards_count = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned'],
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    ).count()

    return {
        'active_visitors_count': active_visitors_count,
        'unclaimed_lf_count': unclaimed_lf_count,
        'overstay_count': overstay_count,
        'active_greencards_count': active_greencards_count,
        'overdue_greencards_count': overdue_greencards_count,
        'current_time': now,
    }
