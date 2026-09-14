from visitors.models import Visitor
from lostfound.models import LostFoundItem
from gatepass.models import GatePass
from core.models import SecurityGate, Property
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

    # 2. Multi-Property Support
    all_properties = Property.objects.filter(is_active=True).order_by('code')
    current_property_id = request.session.get('current_property_id')
    current_property = None
    is_global_property_mode = False

    if current_property_id == 'ALL':
        is_global_property_mode = True
    elif current_property_id:
        current_property = all_properties.filter(id=current_property_id).first()
    
    if not current_property and not is_global_property_mode:
        if getattr(request.user, 'assigned_property', None):
            current_property = request.user.assigned_property
        else:
            current_property = all_properties.first()
        if current_property:
            request.session['current_property_id'] = current_property.id

    # 3. Gates
    if current_property:
        all_gates = current_property.gates.filter(is_active=True).order_by('code')
    else:
        all_gates = SecurityGate.objects.filter(is_active=True).order_by('code')
    
    current_gate_id = request.session.get('current_gate_id')
    current_gate = None
    if current_gate_id:
        current_gate = all_gates.filter(id=current_gate_id).first()
    
    if not current_gate:
        if getattr(request.user, 'assigned_gate', None) and (not current_property or request.user.assigned_gate.property == current_property):
            current_gate = request.user.assigned_gate
        else:
            current_gate = all_gates.first()
        if current_gate:
            request.session['current_gate_id'] = current_gate.id

    # 4. Filtered Telemetry by Current Property (or Global if ALL)
    vis_qs = Visitor.objects.filter(status='active')
    lf_qs = LostFoundItem.objects.filter(status='unclaimed')
    gp_active_qs = GatePass.objects.filter(card_type='GREEN', status__in=['active', 'partially_returned'])
    gp_overdue_qs = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned'],
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    )

    if current_property:
        vis_qs = vis_qs.filter(property=current_property)
        lf_qs = lf_qs.filter(property=current_property)
        gp_active_qs = gp_active_qs.filter(property=current_property)
        gp_overdue_qs = gp_overdue_qs.filter(property=current_property)

    active_visitors_count = vis_qs.count()
    unclaimed_lf_count = lf_qs.count()
    active_greencards_count = gp_active_qs.count()
    overdue_greencards_count = gp_overdue_qs.count()

    overstay_count = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    )
    if current_property:
        overstay_count = overstay_count.filter(property=current_property)
    overstay_count = overstay_count.count()

    is_admin_user = (request.user.is_superuser or request.user.role in ('director', 'supervisor'))

    return {
        'T': T,
        'lang': lang,
        'is_rtl': (lang == 'ar'),
        'all_properties': all_properties,
        'current_property': current_property,
        'is_global_property_mode': is_global_property_mode,
        'all_gates': all_gates,
        'current_gate': current_gate,
        'active_visitors_count': active_visitors_count,
        'unclaimed_lf_count': unclaimed_lf_count,
        'overstay_count': overstay_count,
        'active_greencards_count': active_greencards_count,
        'overdue_greencards_count': overdue_greencards_count,
        'is_admin_user': is_admin_user,
        'current_time': now,
    }
