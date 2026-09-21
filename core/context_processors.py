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

    # 2. Multi-Property & Cluster Support
    if hasattr(request.user, 'get_accessible_properties'):
        accessible_properties = request.user.get_accessible_properties()
    else:
        accessible_properties = Property.objects.filter(is_active=True).order_by('code')

    current_property_id = request.session.get('current_property_id')
    current_property = None
    is_global_property_mode = False

    if current_property_id == 'ALL':
        is_global_property_mode = True
    elif current_property_id:
        current_property = accessible_properties.filter(id=current_property_id).first()
    
    if not current_property and not is_global_property_mode:
        if getattr(request.user, 'role', '') in ('cluster_director', 'saas_owner') or (request.user.is_superuser and not getattr(request.user, 'assigned_property', None)):
            is_global_property_mode = True
            request.session['current_property_id'] = 'ALL'
        elif getattr(request.user, 'assigned_property', None) and request.user.assigned_property in accessible_properties:
            current_property = request.user.assigned_property
            request.session['current_property_id'] = current_property.id
        else:
            current_property = accessible_properties.first()
            if current_property:
                request.session['current_property_id'] = current_property.id

    # 3. Gates
    if current_property:
        all_gates = current_property.gates.filter(is_active=True).order_by('code')
    else:
        all_gates = SecurityGate.objects.filter(property__in=accessible_properties, is_active=True).order_by('code')
    
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

    # 4. Filtered Telemetry by Current Property (or Cluster/Global if ALL)
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
    else:
        vis_qs = vis_qs.filter(property__in=accessible_properties)
        lf_qs = lf_qs.filter(property__in=accessible_properties)
        gp_active_qs = gp_active_qs.filter(property__in=accessible_properties)
        gp_overdue_qs = gp_overdue_qs.filter(property__in=accessible_properties)

    active_visitors_count = vis_qs.count()
    unclaimed_lf_count = lf_qs.count()
    active_greencards_count = gp_active_qs.count()
    overdue_greencards_count = gp_overdue_qs.count()

    overstay_visitors = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    )
    if current_property:
        overstay_visitors = overstay_visitors.filter(property=current_property)
    else:
        overstay_visitors = overstay_visitors.filter(property__in=accessible_properties)
    overstay_count = overstay_visitors.count()

    # 5. Live Notifications / Operational Alerts
    live_alerts = []
    for p in gp_overdue_qs.select_related('property')[:4]:
        live_alerts.append({
            'type': 'danger',
            'icon': '🚨',
            'title': f"Overdue Return: {p.pass_number}",
            'desc': f"Cargo for {p.carrier_company or p.carrier_name} exceeded return window.",
            'url': f"/gatepass/{p.id}/",
            'time': p.expected_return_date,
        })
    for v in overstay_visitors[:4]:
        live_alerts.append({
            'type': 'warning',
            'icon': '⏱️',
            'title': f"Visitor Overstay: {v.full_name}",
            'desc': f"Pass #{v.pass_number} on site past checkout time.",
            'url': f"/visitors/{v.id}/",
            'time': v.expected_checkout_time,
        })
    for lf in lf_qs.filter(value_tier='high_value')[:3]:
        live_alerts.append({
            'type': 'info',
            'icon': '💎',
            'title': f"High-Value Item in Custody: {lf.title}",
            'desc': f"Ref #{lf.reference_number} stored in {lf.storage_location}.",
            'url': f"/lost-and-found/{lf.id}/",
            'time': lf.created_at,
        })

    is_saas_owner = getattr(request.user, 'is_saas_owner', False)
    is_admin_user = (request.user.is_superuser or request.user.role in ('saas_owner', 'director', 'cluster_director', 'supervisor'))
    is_cluster_director = getattr(request.user, 'is_cluster_director', False)

    return {
        'T': T,
        'lang': lang,
        'is_rtl': (lang == 'ar'),
        'all_properties': accessible_properties,
        'current_property': current_property,
        'is_global_property_mode': is_global_property_mode,
        'is_saas_owner': is_saas_owner,
        'is_cluster_director': is_cluster_director,
        'cluster_count': accessible_properties.count(),
        'all_gates': all_gates,
        'current_gate': current_gate,
        'active_visitors_count': active_visitors_count,
        'unclaimed_lf_count': unclaimed_lf_count,
        'overstay_count': overstay_count,
        'active_greencards_count': active_greencards_count,
        'overdue_greencards_count': overdue_greencards_count,
        'live_alerts': live_alerts,
        'total_alert_notifications': len(live_alerts),
        'is_admin_user': is_admin_user,
        'current_time': now,
    }
