from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from visitors.models import Visitor, DepartmentHost
from lostfound.models import LostFoundItem
from gatepass.models import GatePass
from .models import Property, User, SecurityAuditLog, SecurityGate

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            if getattr(user, 'role', '') == 'saas_owner':
                messages.success(request, f"Welcome back, Platform Owner @{user.username}! Accessing SaaS Vendor Command Hub.")
                return redirect('super_admin_dashboard')
            messages.success(request, f"Welcome back, Officer {user.get_full_name() or user.username}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid security badge username or password.")
            
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.info(request, "You have logged out of the Security Management System.")
    return redirect('login')

@login_required
def dashboard_view(request):
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Multi-Property scoping
    current_prop_id = request.session.get('current_property_id')
    current_prop = None
    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
    if current_prop_id and current_prop_id != 'ALL':
        current_prop = accessible_properties.filter(id=current_prop_id).first()
    elif not current_prop_id:
        if getattr(request.user, 'assigned_property', None) and accessible_properties.filter(pk=request.user.assigned_property_id).exists():
            current_prop = request.user.assigned_property
        else:
            current_prop = accessible_properties.first()

    # SaaS Subscription Suspension Gate
    if not (request.user.is_superuser or getattr(request.user, 'role', '') == 'saas_owner'):
        if current_prop and current_prop.subscription_status == 'suspended':
            return redirect('subscription_suspended')

    # 1. Live Visitor KPI counts
    active_visitors = Visitor.objects.filter(status='active').select_related('host_department', 'checked_in_by', 'property')
    today_checkins_qs = Visitor.objects.filter(check_in_time__gte=today_start)
    today_checkouts_qs = Visitor.objects.filter(check_out_time__gte=today_start)
    overstay_visitors = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    )
    
    # 2. Lost & Found metrics
    unclaimed_lf = LostFoundItem.objects.filter(status='unclaimed').select_related('property')
    today_lf_qs = LostFoundItem.objects.filter(created_at__gte=today_start)

    # 3. Material Gate Pass metrics
    active_greencards = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned']
    ).select_related('from_department', 'property')
    total_redcards_qs = GatePass.objects.filter(card_type='RED')
    recent_gatepasses_qs = GatePass.objects.select_related('from_department', 'property').all()
    recent_visitors_qs = Visitor.objects.select_related('property').all()
    recent_lostfound_qs = LostFoundItem.objects.select_related('property').all()
    recent_audits_qs = SecurityAuditLog.objects.select_related('property', 'gate').all()

    # Apply property scoping if not Global/Cluster ALL mode
    if current_prop:
        active_visitors = active_visitors.filter(property=current_prop)
        today_checkins_qs = today_checkins_qs.filter(property=current_prop)
        today_checkouts_qs = today_checkouts_qs.filter(property=current_prop)
        overstay_visitors = overstay_visitors.filter(property=current_prop)
        unclaimed_lf = unclaimed_lf.filter(property=current_prop)
        today_lf_qs = today_lf_qs.filter(property=current_prop)
        active_greencards = active_greencards.filter(property=current_prop)
        total_redcards_qs = total_redcards_qs.filter(property=current_prop)
        recent_gatepasses_qs = recent_gatepasses_qs.filter(property=current_prop)
        recent_visitors_qs = recent_visitors_qs.filter(property=current_prop)
        recent_lostfound_qs = recent_lostfound_qs.filter(property=current_prop)
        recent_audits_qs = recent_audits_qs.filter(Q(property=current_prop) | Q(gate__property=current_prop))
    else:
        # Scope to user's accessible cluster properties
        active_visitors = active_visitors.filter(property__in=accessible_properties)
        today_checkins_qs = today_checkins_qs.filter(property__in=accessible_properties)
        today_checkouts_qs = today_checkouts_qs.filter(property__in=accessible_properties)
        overstay_visitors = overstay_visitors.filter(property__in=accessible_properties)
        unclaimed_lf = unclaimed_lf.filter(property__in=accessible_properties)
        today_lf_qs = today_lf_qs.filter(property__in=accessible_properties)
        active_greencards = active_greencards.filter(property__in=accessible_properties)
        total_redcards_qs = total_redcards_qs.filter(property__in=accessible_properties)
        recent_gatepasses_qs = recent_gatepasses_qs.filter(property__in=accessible_properties)
        recent_visitors_qs = recent_visitors_qs.filter(property__in=accessible_properties)
        recent_lostfound_qs = recent_lostfound_qs.filter(property__in=accessible_properties)
        recent_audits_qs = recent_audits_qs.filter(Q(property__in=accessible_properties) | Q(gate__property__in=accessible_properties))

    cluster_properties_telemetry = []
    if not current_prop:
        for p in accessible_properties:
            p_gates = p.gates.filter(is_active=True).count()
            p_staff = p.personnel.filter(is_on_duty=True).count()
            p_vis = p.visitors.filter(status='active').count()
            p_green = p.gate_passes.filter(card_type='GREEN', status__in=['active', 'partially_returned']).count()
            p_overdue = p.gate_passes.filter(
                card_type='GREEN',
                status__in=['active', 'partially_returned'],
                expected_return_date__isnull=False,
                expected_return_date__lt=now
            ).count()
            p_red = p.gate_passes.filter(card_type='RED').count()
            cluster_properties_telemetry.append({
                'property': p,
                'gates_count': p_gates,
                'staff_count': p_staff,
                'active_visitors': p_vis,
                'active_greencards': p_green,
                'overdue_greencards': p_overdue,
                'total_redcards': p_red,
            })

    active_count = active_visitors.count()
    today_checkins = today_checkins_qs.count()
    today_checkouts = today_checkouts_qs.count()
    overstay_count = overstay_visitors.count()
    unclaimed_count = unclaimed_lf.count()
    high_value_count = unclaimed_lf.filter(value_tier='high_value').count()
    today_lf_logged = today_lf_qs.count()

    active_greencards_count = active_greencards.count()
    overdue_greencards = active_greencards.filter(
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    )
    overdue_greencards_count = overdue_greencards.count()
    total_redcards_count = total_redcards_qs.count()
    recent_gatepasses = recent_gatepasses_qs[:8]

    recent_visitors = recent_visitors_qs[:8]
    recent_lostfound = recent_lostfound_qs[:6]
    recent_audits = recent_audits_qs[:10]

    # Category breakdown for active visitors
    contractor_count = active_visitors.filter(category='contractor').count()
    delivery_count = active_visitors.filter(category='delivery').count()
    guest_count = active_visitors.filter(category='guest').count()

    context = {
        'active_count': active_count,
        'today_checkins': today_checkins,
        'today_checkouts': today_checkouts,
        'overstay_count': overstay_count,
        'unclaimed_count': unclaimed_count,
        'high_value_count': high_value_count,
        'today_lf_logged': today_lf_logged,
        'active_visitors': active_visitors[:12],
        'overstay_visitors': overstay_visitors[:6],
        'recent_visitors': recent_visitors,
        'recent_lostfound': recent_lostfound,
        'recent_audits': recent_audits,
        'contractor_count': contractor_count,
        'delivery_count': delivery_count,
        'guest_count': guest_count,
        # Gate Pass context
        'active_greencards_count': active_greencards_count,
        'overdue_greencards_count': overdue_greencards_count,
        'total_redcards_count': total_redcards_count,
        'recent_gatepasses': recent_gatepasses,
        'cluster_properties_telemetry': cluster_properties_telemetry,
        'overdue_greencards': overdue_greencards[:5],
        'active_greencards': active_greencards[:6],
    }
    return render(request, 'dashboard.html', context)

@login_required
def audit_log_view(request):
    # Restricted: Only Security Director / Shift Supervisor can view the audit trail
    if not (request.user.is_superuser or request.user.role in ('saas_owner', 'director', 'cluster_director', 'supervisor')):
        messages.error(request, "Access Restricted: The Security Audit Trail is strictly limited to Security Directors and Supervisors.")
        return redirect('dashboard')

    action_filter = request.GET.get('action', 'ALL')
    queryset = SecurityAuditLog.objects.select_related('user', 'gate').all()
    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
    queryset = queryset.filter(Q(property__in=accessible_properties) | Q(gate__property__in=accessible_properties) | Q(property__isnull=True, gate__isnull=True))

    if action_filter == 'DELETIONS':
        queryset = queryset.filter(action__in=['PASS_DELETED', 'GATE_DELETED'])
    elif action_filter == 'EDITS':
        queryset = queryset.filter(action__in=['PASS_EDITED', 'GATE_EDITED'])
    elif action_filter == 'PASSES':
        queryset = queryset.filter(action__in=['PASS_CREATED', 'PASS_EDITED', 'PASS_DELETED', 'CHECK_IN', 'CHECK_OUT'])
    elif action_filter == 'GATES':
        queryset = queryset.filter(action__in=['GATE_ADDED', 'GATE_EDITED', 'GATE_DELETED'])
    elif action_filter != 'ALL':
        queryset = queryset.filter(action=action_filter)

    logs = queryset[:300]
    deletions_count = queryset.filter(action__in=['PASS_DELETED', 'GATE_DELETED']).count()
    edits_count = queryset.filter(action__in=['PASS_EDITED', 'GATE_EDITED']).count()

    return render(request, 'audit_log.html', {
        'logs': logs,
        'action_filter': action_filter,
        'deletions_count': deletions_count,
        'edits_count': edits_count,
    })

@login_required
def universal_search_view(request):
    q = request.GET.get('q', '').strip()
    visitors = []
    lostfound_items = []
    gatepasses = []
    
    if q:
        accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
        visitors = Visitor.objects.filter(
            property__in=accessible_properties
        ).filter(
            Q(full_name__icontains=q) |
            Q(pass_number__icontains=q) |
            Q(phone__icontains=q) |
            Q(id_number__icontains=q) |
            Q(vehicle_plate__icontains=q) |
            Q(company_name__icontains=q)
        )[:20]
        
        lostfound_items = LostFoundItem.objects.filter(
            property__in=accessible_properties
        ).filter(
            Q(reference_number__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__icontains=q) |
            Q(serial_number__icontains=q) |
            Q(found_location__icontains=q) |
            Q(claimant_name__icontains=q)
        )[:20]

        gatepasses = GatePass.objects.filter(
            property__in=accessible_properties
        ).filter(
            Q(pass_number__icontains=q) |
            Q(carrier_name__icontains=q) |
            Q(carrier_phone__icontains=q) |
            Q(destination_entity__icontains=q) |
            Q(vehicle_plate__icontains=q) |
            Q(physical_card_ref__icontains=q) |
            Q(items__item_name__icontains=q) |
            Q(items__serial_asset_tag__icontains=q)
        ).distinct()[:20]
        
    return render(request, 'search_results.html', {
        'q': q,
        'visitors': visitors,
        'lostfound_items': lostfound_items,
        'gatepasses': gatepasses,
    })


@login_required
def gates_list_view(request):
    current_prop_id = request.session.get('current_property_id')
    current_prop = None
    if current_prop_id and current_prop_id != 'ALL':
        current_prop = Property.objects.filter(id=current_prop_id).first()

    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()

    if current_prop and accessible_properties.filter(pk=current_prop.pk).exists():
        gates = SecurityGate.objects.filter(property=current_prop).order_by('code')
    else:
        gates = SecurityGate.objects.filter(property__in=accessible_properties).order_by('code')
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        code = request.POST.get('code', '').strip().upper()
        gate_type = request.POST.get('gate_type', 'service')
        description = request.POST.get('description', '').strip()
        prop_id = request.POST.get('property_id')
        target_property = accessible_properties.filter(pk=prop_id).first() if prop_id else current_prop
        
        if not name or not code:
            messages.error(request, "Gate name and gate code are required.")
        elif SecurityGate.objects.filter(code=code).exists():
            messages.error(request, f"Gate code '{code}' already exists! Please use a unique identifier.")
        else:
            new_gate = SecurityGate.objects.create(
                property=target_property,
                name=name,
                name_ar=name_ar,
                code=code,
                gate_type=gate_type,
                description=description,
                is_active=True
            )
            SecurityAuditLog.objects.create(
                user=request.user,
                gate=new_gate,
                action='GATE_ADDED',
                reference=new_gate.code,
                details=f"New perimeter gate added: {new_gate.name} ({new_gate.code}) by {request.user.username}.",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f"Gate '{new_gate.name}' ({new_gate.code}) successfully added to property register!")
            return redirect('gates_list')
            
    return render(request, 'gates/list.html', {'gates': gates})


@login_required
def switch_duty_gate_view(request, gate_id):
    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
    gate = get_object_or_404(SecurityGate, property__in=accessible_properties, pk=gate_id, is_active=True)
    request.session['current_gate_id'] = gate.id
    user = request.user
    user.assigned_gate = gate
    user.save(update_fields=['assigned_gate'])
    
    messages.success(request, f"Duty Station switched to: {gate.name} ({gate.code})")
    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


def set_language_view(request):
    lang = request.GET.get('lang', 'en')
    if lang in ('ar', 'en'):
        request.session['lang'] = lang
    next_url = request.META.get('HTTP_REFERER') or '/'
    return redirect(next_url)


@login_required
def gate_edit_view(request, gate_id):
    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
    gate = get_object_or_404(SecurityGate, property__in=accessible_properties, pk=gate_id)
    if request.method == 'POST':
        old_name = gate.name
        old_code = gate.code
        
        gate.name = request.POST.get('name', '').strip() or gate.name
        gate.name_ar = request.POST.get('name_ar', '').strip()
        new_code = request.POST.get('code', '').strip().upper()
        if new_code and new_code != gate.code and not SecurityGate.objects.filter(code=new_code).exists():
            gate.code = new_code
        gate.gate_type = request.POST.get('gate_type', gate.gate_type)
        gate.description = request.POST.get('description', '').strip()
        gate.is_active = (request.POST.get('is_active') == 'on')
        gate.save()

        SecurityAuditLog.objects.create(
            user=request.user,
            gate=gate,
            action='GATE_EDITED',
            reference=gate.code,
            details=f"Gate '{gate.code}' updated by {request.user.username}. Name: {gate.name} (was {old_name}). Active: {gate.is_active}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Gate {gate.code} ({gate.name}) updated successfully!")
    return redirect('gates_list')


@login_required
def gate_delete_view(request, gate_id):
    accessible_properties = request.user.get_accessible_properties() if hasattr(request.user, 'get_accessible_properties') else Property.objects.none()
    gate = get_object_or_404(SecurityGate, property__in=accessible_properties, pk=gate_id)
    if request.method == 'POST':
        reason = request.POST.get('deletion_reason', '').strip() or 'Deactivated by administrator'
        gate_code = gate.code
        gate_name = gate.name

        # If gate has passes or visitors, safely deactivate it to maintain historical integrity
        has_passes = gate.gate_passes.exists() or gate.visitors.exists()
        if has_passes:
            gate.is_active = False
            gate.save(update_fields=['is_active'])
            action_desc = f"Deactivated gate '{gate_code}' ({gate_name}) (has linked pass records). Reason: {reason}."
        else:
            gate.delete()
            action_desc = f"Permanently deleted gate '{gate_code}' ({gate_name}). Reason: {reason}."

        SecurityAuditLog.objects.create(
            user=request.user,
            action='GATE_DELETED',
            reference=gate_code,
            details=action_desc,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        messages.success(request, f"Gate {gate_code} has been deactivated/removed. Audit trail entry created.")
    return redirect('gates_list')


def subscription_suspended_view(request):
    prop_name = "Your Facility"
    prop_code = ""
    prop = getattr(request.user, 'assigned_property', None)
    if prop:
        prop_name = prop.name_ar if request.session.get('lang') == 'ar' and prop.name_ar else prop.name
        prop_code = prop.code
    return render(request, 'subscription_suspended.html', {
        'prop_name': prop_name,
        'prop_code': prop_code
    })
