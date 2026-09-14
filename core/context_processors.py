from visitors.models import Visitor
from lostfound.models import LostFoundItem
from gatepass.models import GatePass
from core.models import SecurityGate
from core.translations import TRANSLATIONS
from django.utils import timezone

def security_context(request):
    # 1. Language & Localization
    lang = request.session.get('lang')
    if not lang:
        lang = request.GET.get('lang', 'en')
    if 'lang' in request.GET and request.GET['lang'] in ('ar', 'en'):
        lang = request.GET['lang']
        request.session['lang'] = lang
    if lang not in ('ar', 'en'):
        lang = 'en'
    
    T = TRANSLATIONS.get(lang, TRANSLATIONS['en'])

    if not request.user.is_authenticated:
        return {
            'T': T,
            'lang': lang,
            'is_rtl': (lang == 'ar'),
        }
    
    now = timezone.now()

    # 2. Gates
    all_gates = SecurityGate.objects.filter(is_active=True).order_by('code')
    
    current_gate_id = request.session.get('current_gate_id')
    current_gate = None
    if current_gate_id:
        current_gate = all_gates.filter(id=current_gate_id).first()
    
    if not current_gate:
        if getattr(request.user, 'assigned_gate', None):
            current_gate = request.user.assigned_gate
        else:
            current_gate = all_gates.first()
        if current_gate:
            request.session['current_gate_id'] = current_gate.id

    # 3. Telemetry Counts
    active_visitors_count = Visitor.objects.filter(status='active').count()
    unclaimed_lf_count = LostFoundItem.objects.filter(status='unclaimed').count()
    
    overstay_count = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    ).count()

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
        'T': T,
        'lang': lang,
        'is_rtl': (lang == 'ar'),
        'all_gates': all_gates,
        'current_gate': current_gate,
        'active_visitors_count': active_visitors_count,
        'unclaimed_lf_count': unclaimed_lf_count,
        'overstay_count': overstay_count,
        'active_greencards_count': active_greencards_count,
        'overdue_greencards_count': overdue_greencards_count,
        'current_time': now,
    }
