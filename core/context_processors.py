from visitors.models import Visitor
from lostfound.models import LostFoundItem
from django.utils import timezone

def security_context(request):
    if not request.user.is_authenticated:
        return {}
    
    # Active on-premises visitors count
    active_visitors_count = Visitor.objects.filter(status='active').count()
    unclaimed_lf_count = LostFoundItem.objects.filter(status='unclaimed').count()
    
    # Overstaying visitors
    now = timezone.now()
    overstay_count = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    ).count()

    return {
        'active_visitors_count': active_visitors_count,
        'unclaimed_lf_count': unclaimed_lf_count,
        'overstay_count': overstay_count,
        'current_time': now,
    }
