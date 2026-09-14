from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from .models import Property, SecurityGate, User, SecurityAuditLog
from visitors.models import Visitor
from gatepass.models import GatePass
from lostfound.models import LostFoundItem

def is_super_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'director')

@login_required
def super_admin_dashboard_view(request):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted: The Super Admin Command Hub is restricted to Corporate Directors and System Administrators.")
        return redirect('dashboard')

    now = timezone.now()
    properties_qs = Property.objects.all().order_by('code')

    # Build annotated list of properties with live telemetry
    properties_data = []
    for prop in properties_qs:
        gates_count = prop.gates.count()
        staff_count = prop.personnel.count()
        active_visitors = prop.visitors.filter(status='active').count()
        active_greencards = prop.gate_passes.filter(card_type='GREEN', status__in=['active', 'partially_returned']).count()
        overdue_greencards = prop.gate_passes.filter(
            card_type='GREEN',
            status__in=['active', 'partially_returned'],
            expected_return_date__isnull=False,
            expected_return_date__lt=now
        ).count()
        total_redcards = prop.gate_passes.filter(card_type='RED').count()
        unclaimed_lf = prop.lost_found_items.filter(status='unclaimed').count()

        properties_data.append({
            'property': prop,
            'gates_count': gates_count,
            'staff_count': staff_count,
            'active_visitors': active_visitors,
            'active_greencards': active_greencards,
            'overdue_greencards': overdue_greencards,
            'total_redcards': total_redcards,
            'unclaimed_lf': unclaimed_lf,
        })

    # Global portfolio telemetry
    total_properties = properties_qs.count()
    active_properties = properties_qs.filter(is_active=True).count()
    total_gates = SecurityGate.objects.count()
    total_users = User.objects.count()
    on_duty_users = User.objects.filter(is_on_duty=True).count()
    total_active_visitors = Visitor.objects.filter(status='active').count()
    total_active_greencards = GatePass.objects.filter(card_type='GREEN', status__in=['active', 'partially_returned']).count()
    total_overdue_greencards = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned'],
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    ).count()

    # Personnel roster
    users_qs = User.objects.select_related('assigned_property', 'assigned_gate').order_by('-is_on_duty', 'username')

    # Super Admin Audits
    admin_audits = SecurityAuditLog.objects.filter(
        action__in=[
            'PROPERTY_CREATED', 'PROPERTY_EDITED', 'PROPERTY_DEACTIVATED',
            'USER_CREATED', 'USER_EDITED', 'GATE_ADDED', 'GATE_EDITED', 'GATE_DELETED'
        ]
    ).select_related('user', 'property', 'gate')[:25]

    all_gates = SecurityGate.objects.filter(is_active=True).select_related('property').order_by('code')

    context = {
        'properties_data': properties_data,
        'total_properties': total_properties,
        'active_properties': active_properties,
        'total_gates': total_gates,
        'total_users': total_users,
        'on_duty_users': on_duty_users,
        'total_active_visitors': total_active_visitors,
        'total_active_greencards': total_active_greencards,
        'total_overdue_greencards': total_overdue_greencards,
        'users_list': users_qs,
        'admin_audits': admin_audits,
        'all_gates': all_gates,
        'property_types': Property.PROPERTY_TYPE_CHOICES,
        'role_choices': User.ROLE_CHOICES,
        'shift_choices': [
            ('morning', 'Morning Shift (07:00 - 15:00)'),
            ('afternoon', 'Afternoon Shift (15:00 - 23:00)'),
            ('night', 'Night Shift (23:00 - 07:00)')
        ],
    }
    return render(request, 'admin/super_admin.html', context)


@login_required
def property_create_view(request):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted: You do not have permission to create properties.")
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        code = request.POST.get('code', '').strip().upper()
        property_type = request.POST.get('property_type', 'hotel')
        city = request.POST.get('city', 'Riyadh').strip()
        address = request.POST.get('address', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()
        manager_name = request.POST.get('manager_name', '').strip()
        create_default_gate = (request.POST.get('create_default_gate') == 'on')

        if not name or not code:
            messages.error(request, "Property English Name and Unique Code are required.")
            return redirect('super_admin_dashboard')

        if Property.objects.filter(code=code).exists():
            messages.error(request, f"Property code '{code}' already exists! Choose a unique identifier.")
            return redirect('super_admin_dashboard')

        prop = Property.objects.create(
            name=name,
            name_ar=name_ar,
            code=code,
            property_type=property_type,
            city=city,
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            manager_name=manager_name,
            is_active=True
        )

        # Create default main gate if requested
        if create_default_gate:
            gate_code = f"{code}-GATE01"
            if not SecurityGate.objects.filter(code=gate_code).exists():
                SecurityGate.objects.create(
                    property=prop,
                    name="Main Security Gate & Barrier",
                    name_ar="البوابة والحاجز الأمني الرئيسي",
                    code=gate_code,
                    gate_type="main",
                    description="Primary perimeter vehicle barrier and visitor screening checkpoint.",
                    is_active=True
                )

        SecurityAuditLog.objects.create(
            user=request.user,
            property=prop,
            action='PROPERTY_CREATED',
            reference=prop.code,
            details=f"New property registered: {prop.name} [{prop.code}] in {prop.city} by {request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"Property '{prop.name}' ({prop.code}) registered successfully!")
    
    return redirect('super_admin_dashboard')


@login_required
def property_edit_view(request, property_id):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted: You do not have permission to edit properties.")
        return redirect('dashboard')

    prop = get_object_or_404(Property, pk=property_id)

    if request.method == 'POST':
        prop.name = request.POST.get('name', '').strip() or prop.name
        prop.name_ar = request.POST.get('name_ar', '').strip()
        new_code = request.POST.get('code', '').strip().upper()
        if new_code and new_code != prop.code and not Property.objects.filter(code=new_code).exists():
            prop.code = new_code
        prop.property_type = request.POST.get('property_type', prop.property_type)
        prop.city = request.POST.get('city', prop.city).strip()
        prop.address = request.POST.get('address', prop.address).strip()
        prop.contact_email = request.POST.get('contact_email', prop.contact_email).strip()
        prop.contact_phone = request.POST.get('contact_phone', prop.contact_phone).strip()
        prop.manager_name = request.POST.get('manager_name', prop.manager_name).strip()
        prop.is_active = (request.POST.get('is_active') == 'on')
        prop.save()

        SecurityAuditLog.objects.create(
            user=request.user,
            property=prop,
            action='PROPERTY_EDITED',
            reference=prop.code,
            details=f"Property '{prop.code}' details updated by {request.user.username}. Active: {prop.is_active}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"Property '{prop.name}' [{prop.code}] updated successfully!")

    return redirect('super_admin_dashboard')


@login_required
def property_toggle_view(request, property_id):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    prop = get_object_or_404(Property, pk=property_id)
    prop.is_active = not prop.is_active
    prop.save(update_fields=['is_active'])

    action = 'PROPERTY_DEACTIVATED' if not prop.is_active else 'PROPERTY_EDITED'
    SecurityAuditLog.objects.create(
        user=request.user,
        property=prop,
        action=action,
        reference=prop.code,
        details=f"Property status toggled to {'ACTIVE' if prop.is_active else 'DEACTIVATED'} by {request.user.username}.",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    status_str = "activated" if prop.is_active else "deactivated"
    messages.success(request, f"Property '{prop.name}' has been {status_str}.")
    return redirect('super_admin_dashboard')


@login_required
def property_switch_view(request, property_id):
    """Switch active property context across the whole application session."""
    if str(property_id).upper() == 'ALL':
        request.session['current_property_id'] = 'ALL'
        request.session.pop('current_gate_id', None)
        messages.info(request, "Switched to Global Portfolio Mode: Viewing all properties.")
    else:
        prop = get_object_or_404(Property, pk=property_id, is_active=True)
        request.session['current_property_id'] = prop.id
        first_gate = prop.gates.filter(is_active=True).first()
        if first_gate:
            request.session['current_gate_id'] = first_gate.id
            if hasattr(request.user, 'assigned_gate'):
                request.user.assigned_gate = first_gate
                request.user.save(update_fields=['assigned_gate'])
        else:
            request.session.pop('current_gate_id', None)
        
        display_name = prop.name_ar if request.session.get('lang') == 'ar' and prop.name_ar else prop.name
        messages.success(request, f"Active facility switched to: {display_name} [{prop.code}]")

    next_url = request.META.get('HTTP_REFERER') or 'dashboard'
    return redirect(next_url)


@login_required
def user_create_view(request):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted: You do not have permission to provision security staff.")
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'officer')
        badge_number = request.POST.get('badge_number', '').strip()
        phone = request.POST.get('phone', '').strip()
        shift = request.POST.get('shift', 'morning')
        property_id = request.POST.get('property_id')
        gate_id = request.POST.get('gate_id')
        is_on_duty = (request.POST.get('is_on_duty') == 'on')

        if not username or not password:
            messages.error(request, "Username and temporary password are required to create a security account.")
            return redirect('super_admin_dashboard')

        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists. Please select another username.")
            return redirect('super_admin_dashboard')

        user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role=role,
            badge_number=badge_number,
            phone=phone,
            shift=shift,
            is_on_duty=is_on_duty,
        )
        user.set_password(password)

        if property_id:
            user.assigned_property = Property.objects.filter(pk=property_id).first()
        if gate_id:
            user.assigned_gate = SecurityGate.objects.filter(pk=gate_id).first()

        user.save()

        SecurityAuditLog.objects.create(
            user=request.user,
            property=user.assigned_property,
            gate=user.assigned_gate,
            action='USER_CREATED',
            reference=user.username,
            details=f"Security user '{user.username}' ({user.get_role_display()}, Badge: {user.badge_number}) created and assigned to {user.assigned_property} by {request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"Security personnel '{user.get_full_name() or user.username}' ({user.badge_number}) provisioned successfully!")

    return redirect('super_admin_dashboard')


@login_required
def user_edit_view(request, user_id):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    target_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', target_user.first_name).strip()
        target_user.last_name = request.POST.get('last_name', target_user.last_name).strip()
        target_user.email = request.POST.get('email', target_user.email).strip()
        target_user.role = request.POST.get('role', target_user.role)
        target_user.badge_number = request.POST.get('badge_number', target_user.badge_number).strip()
        target_user.phone = request.POST.get('phone', target_user.phone).strip()
        target_user.shift = request.POST.get('shift', target_user.shift)
        target_user.is_on_duty = (request.POST.get('is_on_duty') == 'on')

        new_password = request.POST.get('password', '').strip()
        if new_password:
            target_user.set_password(new_password)

        prop_id = request.POST.get('property_id')
        if prop_id:
            target_user.assigned_property = Property.objects.filter(pk=prop_id).first()
        else:
            target_user.assigned_property = None

        gate_id = request.POST.get('gate_id')
        if gate_id:
            target_user.assigned_gate = SecurityGate.objects.filter(pk=gate_id).first()
        else:
            target_user.assigned_gate = None

        target_user.save()

        SecurityAuditLog.objects.create(
            user=request.user,
            property=target_user.assigned_property,
            gate=target_user.assigned_gate,
            action='USER_EDITED',
            reference=target_user.username,
            details=f"Security personnel '{target_user.username}' updated by {request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"User '{target_user.username}' profile updated successfully!")

    return redirect('super_admin_dashboard')
