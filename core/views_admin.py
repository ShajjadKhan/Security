from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Sum
from decimal import Decimal
import datetime
from .models import Property, SecurityGate, User, SecurityAuditLog, PropertySubscriptionInvoice
from visitors.models import Visitor
from gatepass.models import GatePass
from lostfound.models import LostFoundItem

MANAGER_ROLES = ('director', 'cluster_director', 'supervisor')

def is_platform_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == 'saas_owner')

def is_security_manager(user):
    return user.is_authenticated and (
        is_platform_admin(user) or user.role in MANAGER_ROLES or user.cluster_properties.exists()
    )

def is_super_admin(user):
    return is_platform_admin(user)

def accessible_properties_for(user):
    if hasattr(user, 'get_accessible_properties'):
        return user.get_accessible_properties()
    return Property.objects.none()

def require_accessible_property(user, property_id):
    return get_object_or_404(accessible_properties_for(user), pk=property_id)

@login_required
def super_admin_dashboard_view(request):
    if not is_super_admin(request.user):
        messages.error(request, "Access Restricted: The Super Admin Command Hub is restricted to the Software Vendor / SaaS Platform Owner.")
        return redirect('dashboard')

    now = timezone.now()
    today = now.date()
    properties_qs = accessible_properties_for(request.user)
    platform_admin = is_platform_admin(request.user)

    # SaaS Revenue & Monthly Fee Telemetry
    total_mrr = properties_qs.filter(is_active=True).aggregate(mrr=Sum('monthly_fee'))['mrr'] or Decimal('0.00')
    
    all_invoices = PropertySubscriptionInvoice.objects.select_related('property').filter(property__in=properties_qs).order_by('-created_at')
    total_collected_all = all_invoices.filter(status='paid').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')
    total_due_all = all_invoices.filter(status__in=['unpaid', 'overdue']).aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

    active_subscriptions = properties_qs.filter(subscription_status__in=['active', 'trial']).count()
    past_due_subscriptions = properties_qs.filter(subscription_status='past_due').count()
    suspended_subscriptions = properties_qs.filter(subscription_status='suspended').count()

    # Build annotated list of client properties with SaaS subscription & operational telemetry
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

        first_admin = prop.personnel.filter(role__in=['director', 'cluster_director']).first()
        latest_invoice = prop.invoices.first()
        collected_for_prop = prop.invoices.filter(status='paid').aggregate(s=Sum('amount'))['s'] or Decimal('0.00')

        properties_data.append({
            'property': prop,
            'plan_tier_display': prop.get_plan_tier_display(),
            'monthly_fee': prop.monthly_fee,
            'subscription_status': prop.subscription_status,
            'subscription_status_display': prop.get_subscription_status_display(),
            'buyer_company': prop.buyer_company,
            'buyer_name': prop.buyer_name or prop.manager_name,
            'buyer_phone': prop.buyer_phone or prop.contact_phone,
            'buyer_email': prop.buyer_email or prop.contact_email,
            'first_admin': first_admin,
            'latest_invoice': latest_invoice,
            'total_collected': collected_for_prop,
            'gates_count': gates_count,
            'staff_count': staff_count,
            'active_visitors': active_visitors,
            'active_greencards': active_greencards,
            'overdue_greencards': overdue_greencards,
            'total_redcards': total_redcards,
            'unclaimed_lf': unclaimed_lf,
        })

    # Global portfolio operational totals
    total_properties = properties_qs.count()
    active_properties = properties_qs.filter(is_active=True).count()
    total_gates = SecurityGate.objects.filter(property__in=properties_qs).count()
    total_users = User.objects.filter(Q(assigned_property__in=properties_qs) | Q(cluster_properties__in=properties_qs)).distinct().count()
    on_duty_users = User.objects.filter(Q(assigned_property__in=properties_qs) | Q(cluster_properties__in=properties_qs), is_on_duty=True).distinct().count()
    total_active_visitors = Visitor.objects.filter(property__in=properties_qs, status='active').count()
    total_active_greencards = GatePass.objects.filter(property__in=properties_qs, card_type='GREEN', status__in=['active', 'partially_returned']).count()
    total_overdue_greencards = GatePass.objects.filter(
        property__in=properties_qs,
        card_type='GREEN',
        status__in=['active', 'partially_returned'],
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    ).count()

    # Personnel roster
    users_qs = User.objects.filter(
        Q(assigned_property__in=properties_qs) | Q(cluster_properties__in=properties_qs) | Q(pk=request.user.pk)
    ).distinct().select_related('assigned_property', 'assigned_gate').prefetch_related('cluster_properties').order_by('-is_on_duty', 'username')

    # SaaS Platform Audits
    admin_audits = SecurityAuditLog.objects.filter(
        Q(property__in=properties_qs) | Q(gate__property__in=properties_qs),
        action__in=[
            'PROPERTY_CREATED', 'PROPERTY_EDITED', 'PROPERTY_DEACTIVATED',
            'USER_CREATED', 'USER_EDITED', 'GATE_ADDED', 'GATE_EDITED', 'GATE_DELETED',
            'CLIENT_ONBOARDED', 'FEE_COLLECTED', 'SUBSCRIPTION_SUSPENDED',
            'SUBSCRIPTION_REACTIVATED', 'INVOICE_GENERATED'
        ]
    ).select_related('user', 'property', 'gate')[:35]

    all_gates = SecurityGate.objects.filter(property__in=properties_qs, is_active=True).select_related('property').order_by('code')
    directors_list = users_qs.filter(role__in=['director', 'cluster_director', 'supervisor']).order_by('first_name', 'username')

    context = {
        'properties_data': properties_data,
        'all_properties': properties_qs,
        'total_properties': total_properties,
        'active_properties': active_properties,
        'total_mrr': total_mrr,
        'total_collected': total_collected_all,
        'total_due': total_due_all,
        'active_subscriptions': active_subscriptions,
        'past_due_subscriptions': past_due_subscriptions,
        'suspended_subscriptions': suspended_subscriptions,
        'invoices_list': all_invoices[:30],
        'total_gates': total_gates,
        'total_users': total_users,
        'on_duty_users': on_duty_users,
        'total_active_visitors': total_active_visitors,
        'total_active_greencards': total_active_greencards,
        'total_overdue_greencards': total_overdue_greencards,
        'users_list': users_qs,
        'directors_list': directors_list,
        'admin_audits': admin_audits,
        'all_gates': all_gates,
        'property_types': Property.PROPERTY_TYPE_CHOICES,
        'plan_tier_choices': Property.PLAN_TIER_CHOICES,
        'billing_cycle_choices': Property.BILLING_CYCLE_CHOICES,
        'subscription_status_choices': Property.SUBSCRIPTION_STATUS_CHOICES,
        'payment_method_choices': PropertySubscriptionInvoice.PAYMENT_METHOD_CHOICES,
        'role_choices': User.ROLE_CHOICES,
        'platform_admin': platform_admin,
        'shift_choices': [
            ('morning', 'Morning Shift (07:00 - 15:00)'),
            ('afternoon', 'Afternoon Shift (15:00 - 23:00)'),
            ('night', 'Night Shift (23:00 - 07:00)')
        ],
    }
    return render(request, 'admin/super_admin.html', context)


@login_required
def property_create_view(request):
    if not is_platform_admin(request.user):
        messages.error(request, "Access Restricted: You do not have permission to onboard client properties.")
        return redirect('dashboard')

    if request.method == 'POST':
        # Property details
        name = request.POST.get('name', '').strip()
        name_ar = request.POST.get('name_ar', '').strip()
        code = request.POST.get('code', '').strip().upper()
        property_type = request.POST.get('property_type', 'hotel')
        city = request.POST.get('city', 'Riyadh').strip()
        address = request.POST.get('address', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        contact_phone = request.POST.get('contact_phone', '').strip()

        # SaaS Subscription & Billing details
        platform_admin = is_platform_admin(request.user)
        plan_tier = request.POST.get('plan_tier', 'professional') if platform_admin else 'professional'
        monthly_fee_str = request.POST.get('monthly_fee', '1500').strip()
        try:
            monthly_fee = Decimal(monthly_fee_str)
        except Exception:
            monthly_fee = Decimal('1500.00')
        billing_cycle = request.POST.get('billing_cycle', 'monthly') if platform_admin else 'monthly'
        subscription_status = request.POST.get('subscription_status', 'active') if platform_admin else 'active'
        buyer_company = request.POST.get('buyer_company', '').strip()
        buyer_name = request.POST.get('buyer_name', '').strip()
        buyer_phone = request.POST.get('buyer_phone', '').strip()
        buyer_email = request.POST.get('buyer_email', '').strip()
        subscription_notes = request.POST.get('subscription_notes', '').strip()

        # First Admin User Credentials (The Client Director / Buyer account)
        admin_username = request.POST.get('admin_username', '').strip()
        admin_password = request.POST.get('admin_password', '').strip()
        admin_first_name = request.POST.get('admin_first_name', '').strip()
        admin_last_name = request.POST.get('admin_last_name', '').strip()
        admin_role = request.POST.get('admin_role', 'director')
        if not platform_admin and admin_role in ('saas_owner',):
            admin_role = 'director'
        admin_phone = request.POST.get('admin_phone', '').strip()

        create_default_gate = (request.POST.get('create_default_gate') == 'on')
        generate_initial_invoice = (request.POST.get('generate_initial_invoice') == 'on')

        if not name or not code:
            messages.error(request, "Property English Name and Unique Code are required.")
            return redirect('super_admin_dashboard')

        if Property.objects.filter(code=code).exists():
            messages.error(request, f"Property code '{code}' already exists! Choose a unique identifier.")
            return redirect('super_admin_dashboard')

        today = timezone.now().date()
        next_billing = today + timezone.timedelta(days=30)

        prop = Property.objects.create(
            name=name,
            name_ar=name_ar,
            code=code,
            property_type=property_type,
            city=city,
            address=address,
            contact_email=contact_email,
            contact_phone=contact_phone,
            manager_name=buyer_name or f"{admin_first_name} {admin_last_name}".strip(),
            is_active=True,
            plan_tier=plan_tier,
            monthly_fee=monthly_fee,
            billing_cycle=billing_cycle,
            subscription_status=subscription_status,
            next_billing_date=next_billing,
            buyer_company=buyer_company,
            buyer_name=buyer_name,
            buyer_phone=buyer_phone,
            buyer_email=buyer_email,
            subscription_notes=subscription_notes,
        )

        # 1. Provision First Admin User if credentials provided
        first_user = None
        if admin_username and admin_password:
            if not User.objects.filter(username=admin_username).exists():
                first_user = User(
                    username=admin_username,
                    first_name=admin_first_name,
                    last_name=admin_last_name,
                    email=buyer_email or contact_email,
                    role=admin_role,
                    badge_number=f"DIR-{code[-4:]}",
                    phone=admin_phone or buyer_phone,
                    assigned_property=prop,
                    is_on_duty=True
                )
                first_user.set_password(admin_password)
                first_user.save()
                first_user.cluster_properties.add(prop)
                if request.user.role in ('director', 'cluster_director') and not is_platform_admin(request.user):
                    request.user.cluster_properties.add(prop)

        # 2. Create default main gate if requested
        if create_default_gate:
            gate_code = f"{code}-GATE01"
            if not SecurityGate.objects.filter(code=gate_code).exists():
                main_gate = SecurityGate.objects.create(
                    property=prop,
                    name="Main Security Gate & Barrier",
                    name_ar="البوابة والحاجز الأمني الرئيسي",
                    code=gate_code,
                    gate_type="main",
                    description="Primary perimeter vehicle barrier and visitor checkpoint.",
                    is_active=True
                )
                if first_user:
                    first_user.assigned_gate = main_gate
                    first_user.save(update_fields=['assigned_gate'])

        # 3. Create initial monthly invoice
        if generate_initial_invoice:
            month_str = today.strftime("%B %Y")
            inv_code = f"INV-{today.strftime('%Y%m')}-{code[-6:].replace('-', '')}"
            PropertySubscriptionInvoice.objects.create(
                property=prop,
                invoice_number=inv_code,
                billing_period=month_str,
                amount=monthly_fee,
                due_date=today,
                status='paid' if subscription_status == 'active' else 'unpaid',
                payment_method='bank_transfer' if subscription_status == 'active' else '',
                payment_date=today if subscription_status == 'active' else None,
                payment_reference='ONBOARDING-PAYMENT' if subscription_status == 'active' else '',
                notes=f"Initial onboarding subscription fee for {prop.name}"
            )

        SecurityAuditLog.objects.create(
            user=request.user,
            property=prop,
            action='CLIENT_ONBOARDED',
            reference=prop.code,
            details=f"Client property '{prop.code}' onboarded on {plan_tier} plan ({monthly_fee} SAR/mo). First Admin: @{admin_username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        msg = f"Client Property '{prop.name}' [{prop.code}] onboarded successfully! Plan: {monthly_fee} SAR/month."
        if first_user:
            msg += f" First Admin User '@{admin_username}' provisioned."
        messages.success(request, msg)

    return redirect('super_admin_dashboard')


@login_required
def property_edit_view(request, property_id):
    if not is_security_manager(request.user):
        messages.error(request, "Access Restricted: You do not have permission to edit properties.")
        return redirect('dashboard')

    prop = require_accessible_property(request.user, property_id)

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
        
        # SaaS Subscription fields
        if is_platform_admin(request.user):
            prop.plan_tier = request.POST.get('plan_tier', prop.plan_tier)
            monthly_fee_str = request.POST.get('monthly_fee', str(prop.monthly_fee)).strip()
            try:
                prop.monthly_fee = Decimal(monthly_fee_str)
            except Exception:
                pass
            prop.billing_cycle = request.POST.get('billing_cycle', prop.billing_cycle)
            prop.subscription_status = request.POST.get('subscription_status', prop.subscription_status)
        prop.buyer_company = request.POST.get('buyer_company', prop.buyer_company).strip()
        prop.buyer_name = request.POST.get('buyer_name', prop.buyer_name).strip()
        prop.buyer_phone = request.POST.get('buyer_phone', prop.buyer_phone).strip()
        prop.buyer_email = request.POST.get('buyer_email', prop.buyer_email).strip()
        prop.subscription_notes = request.POST.get('subscription_notes', prop.subscription_notes).strip()

        prop.is_active = (request.POST.get('is_active') == 'on')
        prop.save()

        SecurityAuditLog.objects.create(
            user=request.user,
            property=prop,
            action='PROPERTY_EDITED',
            reference=prop.code,
            details=f"Property contract '{prop.code}' updated. Plan: {prop.plan_tier}, Monthly Fee: {prop.monthly_fee} SAR. Status: {prop.subscription_status}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"Client Property '{prop.name}' [{prop.code}] updated successfully!")

    return redirect('super_admin_dashboard')


@login_required
def collect_fee_view(request, property_id):
    """SaaS Vendor collects monthly subscription fee for a client property."""
    if not is_platform_admin(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    prop = require_accessible_property(request.user, property_id)

    if request.method == 'POST':
        amount_str = request.POST.get('amount', str(prop.monthly_fee)).strip()
        try:
            amount = Decimal(amount_str)
        except Exception:
            amount = prop.monthly_fee

        payment_method = request.POST.get('payment_method', 'bank_transfer')
        payment_reference = request.POST.get('payment_reference', '').strip()
        billing_period = request.POST.get('billing_period', timezone.now().strftime('%B %Y')).strip()
        notes = request.POST.get('notes', '').strip()

        today = timezone.now().date()
        inv_code = f"INV-{today.strftime('%Y%m')}-{prop.code[-6:].replace('-', '')}"

        # Find existing unpaid invoice or create new paid invoice
        inv = prop.invoices.filter(billing_period=billing_period, status__in=['unpaid', 'overdue']).first()
        if inv:
            inv.status = 'paid'
            inv.amount = amount
            inv.payment_method = payment_method
            inv.payment_reference = payment_reference
            inv.payment_date = today
            inv.notes = notes
            inv.save()
        else:
            inv = PropertySubscriptionInvoice.objects.create(
                property=prop,
                invoice_number=inv_code if not PropertySubscriptionInvoice.objects.filter(invoice_number=inv_code).exists() else f"{inv_code}-{timezone.now().strftime('%d%H%M')}",
                billing_period=billing_period,
                amount=amount,
                due_date=today,
                status='paid',
                payment_method=payment_method,
                payment_reference=payment_reference,
                payment_date=today,
                notes=notes
            )

        prop.subscription_status = 'active'
        prop.is_active = True
        prop.next_billing_date = today + timezone.timedelta(days=30)
        prop.save(update_fields=['subscription_status', 'is_active', 'next_billing_date'])

        SecurityAuditLog.objects.create(
            user=request.user,
            property=prop,
            action='FEE_COLLECTED',
            reference=inv.invoice_number,
            details=f"Monthly SaaS subscription fee of {amount} SAR collected for {prop.code} via {payment_method}. Ref: {payment_reference}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"✓ Payment of {amount} SAR successfully collected for [{prop.code}] {prop.name}! Invoice #{inv.invoice_number} is PAID.")

    return redirect('super_admin_dashboard')


@login_required
def property_suspend_toggle_view(request, property_id):
    """SaaS Vendor locks/suspends a client property for unpaid dues, or restores access."""
    if not is_platform_admin(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    prop = require_accessible_property(request.user, property_id)
    if prop.subscription_status == 'suspended':
        prop.subscription_status = 'active'
        prop.is_active = True
        action = 'SUBSCRIPTION_REACTIVATED'
        msg = f"Client Property '{prop.name}' [{prop.code}] subscription REACTIVATED! Operational access restored."
    else:
        prop.subscription_status = 'suspended'
        action = 'SUBSCRIPTION_SUSPENDED'
        msg = f"Client Property '{prop.name}' [{prop.code}] subscription SUSPENDED! Workspace locked for unpaid monthly fees."
    
    prop.save(update_fields=['subscription_status', 'is_active'])

    SecurityAuditLog.objects.create(
        user=request.user,
        property=prop,
        action=action,
        reference=prop.code,
        details=f"SaaS subscription status changed to '{prop.subscription_status}' by Platform Owner {request.user.username}.",
        ip_address=request.META.get('REMOTE_ADDR')
    )

    messages.info(request, msg)
    return redirect('super_admin_dashboard')


@login_required
def generate_monthly_invoices_view(request):
    """SaaS Vendor recurring billing runner: generates monthly invoices for all active clients."""
    if not is_platform_admin(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    today = timezone.now().date()
    month_str = today.strftime("%B %Y")
    created_count = 0

    for prop in accessible_properties_for(request.user).filter(is_active=True):
        if not prop.invoices.filter(billing_period=month_str).exists():
            inv_code = f"INV-{today.strftime('%Y%m')}-{prop.code[-6:].replace('-', '')}"
            if PropertySubscriptionInvoice.objects.filter(invoice_number=inv_code).exists():
                inv_code = f"{inv_code}-{timezone.now().strftime('%d%H%M')}"
            
            PropertySubscriptionInvoice.objects.create(
                property=prop,
                invoice_number=inv_code,
                billing_period=month_str,
                amount=prop.monthly_fee,
                due_date=today,
                status='unpaid',
                notes=f"Monthly recurring SaaS subscription invoice for {month_str}"
            )
            created_count += 1

    messages.success(request, f"Generated {created_count} monthly subscription invoices for {month_str}!")
    return redirect('super_admin_dashboard')


@login_required
def property_toggle_view(request, property_id):
    if not is_security_manager(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    prop = require_accessible_property(request.user, property_id)
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
        if not (request.user.is_superuser or request.user.role == 'saas_owner' or getattr(request.user, 'is_cluster_director', False)):
            messages.error(request, "Access Restricted: Single-property accounts cannot switch to multi-facility view.")
            return redirect('dashboard')
        request.session['current_property_id'] = 'ALL'
        request.session.pop('current_gate_id', None)
        if request.user.role == 'saas_owner' or request.user.is_superuser:
            messages.info(request, "Switched to SaaS Portfolio Mode: Viewing all client facilities.")
        else:
            messages.info(request, "Switched to Cluster Overview Mode: Viewing all your assigned facilities.")
    else:
        prop = get_object_or_404(accessible_properties_for(request.user), pk=property_id, is_active=True)
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
    if not is_security_manager(request.user):
        messages.error(request, "Access Restricted: You do not have permission to provision security staff.")
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        password = request.POST.get('password', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'officer')
        if not is_platform_admin(request.user) and role == 'saas_owner':
            role = 'officer'
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

        accessible_props = accessible_properties_for(request.user)
        if property_id:
            user.assigned_property = accessible_props.filter(pk=property_id).first()
        if gate_id:
            user.assigned_gate = SecurityGate.objects.filter(property__in=accessible_props, pk=gate_id).first()

        user.save()

        # Handle cluster properties assignment
        cluster_prop_ids = list(accessible_props.filter(pk__in=request.POST.getlist('cluster_properties')).values_list('pk', flat=True))
        if cluster_prop_ids:
            user.cluster_properties.set(cluster_prop_ids)
        elif user.assigned_property:
            user.cluster_properties.set([user.assigned_property])

        SecurityAuditLog.objects.create(
            user=request.user,
            property=user.assigned_property,
            gate=user.assigned_gate,
            action='USER_CREATED',
            reference=user.username,
            details=f"Security user '{user.username}' ({user.get_role_display()}, Badge: {user.badge_number}) created and assigned to {user.assigned_property} with {user.cluster_properties.count()} cluster properties by {request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"Security personnel '{user.get_full_name() or user.username}' ({user.badge_number}) provisioned successfully!")

    return redirect('super_admin_dashboard')


@login_required
def user_edit_view(request, user_id):
    if not is_security_manager(request.user):
        messages.error(request, "Access Restricted.")
        return redirect('dashboard')

    accessible_props = accessible_properties_for(request.user)
    target_user = get_object_or_404(
        User.objects.filter(Q(assigned_property__in=accessible_props) | Q(cluster_properties__in=accessible_props)).distinct(),
        pk=user_id
    )

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', target_user.first_name).strip()
        target_user.last_name = request.POST.get('last_name', target_user.last_name).strip()
        target_user.email = request.POST.get('email', target_user.email).strip()
        new_role = request.POST.get('role', target_user.role)
        if not is_platform_admin(request.user) and new_role == 'saas_owner':
            new_role = target_user.role
        target_user.role = new_role
        target_user.badge_number = request.POST.get('badge_number', target_user.badge_number).strip()
        target_user.phone = request.POST.get('phone', target_user.phone).strip()
        target_user.shift = request.POST.get('shift', target_user.shift)
        target_user.is_on_duty = (request.POST.get('is_on_duty') == 'on')

        new_password = request.POST.get('password', '').strip()
        if new_password:
            target_user.set_password(new_password)

        prop_id = request.POST.get('property_id')
        if prop_id:
            target_user.assigned_property = accessible_props.filter(pk=prop_id).first()
        else:
            target_user.assigned_property = None

        gate_id = request.POST.get('gate_id')
        if gate_id:
            target_user.assigned_gate = SecurityGate.objects.filter(property__in=accessible_props, pk=gate_id).first()
        else:
            target_user.assigned_gate = None

        target_user.save()

        # Update cluster properties
        cluster_prop_ids = list(accessible_props.filter(pk__in=request.POST.getlist('cluster_properties')).values_list('pk', flat=True))
        target_user.cluster_properties.set(cluster_prop_ids)

        SecurityAuditLog.objects.create(
            user=request.user,
            property=target_user.assigned_property,
            gate=target_user.assigned_gate,
            action='USER_EDITED',
            reference=target_user.username,
            details=f"Security personnel '{target_user.username}' updated ({target_user.cluster_properties.count()} cluster properties) by {request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR')
        )

        messages.success(request, f"User '{target_user.username}' profile updated successfully!")

    return redirect('super_admin_dashboard')
