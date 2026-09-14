from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import GatePass, GatePassItem
from visitors.models import DepartmentHost
from core.models import SecurityAuditLog, SecurityGate

@login_required
def gatepass_list(request):
    card_filter = request.GET.get('card', 'all')
    status_filter = request.GET.get('status', 'all')
    q = request.GET.get('q', '').strip()

    queryset = GatePass.objects.select_related('from_department', 'dispatched_by').prefetch_related('items').all()

    if card_filter in ('GREEN', 'RED'):
        queryset = queryset.filter(card_type=card_filter)

    now = timezone.now()
    if status_filter == 'active':
        queryset = queryset.filter(status='active', card_type='GREEN')
    elif status_filter == 'overdue':
        queryset = queryset.filter(
            card_type='GREEN',
            status__in=['active', 'partially_returned'],
            expected_return_date__isnull=False,
            expected_return_date__lt=now
        )
    elif status_filter == 'returned':
        queryset = queryset.filter(status='fully_returned')
    elif status_filter == 'dispatched_closed':
        queryset = queryset.filter(card_type='RED')

    if q:
        queryset = queryset.filter(
            Q(pass_number__icontains=q) |
            Q(carrier_name__icontains=q) |
            Q(carrier_phone__icontains=q) |
            Q(destination_entity__icontains=q) |
            Q(vehicle_plate__icontains=q) |
            Q(physical_card_ref__icontains=q) |
            Q(items__item_name__icontains=q) |
            Q(items__serial_asset_tag__icontains=q)
        ).distinct()

    # Telemetry counts
    green_active_count = GatePass.objects.filter(card_type='GREEN', status='active').count()
    green_overdue_count = GatePass.objects.filter(
        card_type='GREEN',
        status__in=['active', 'partially_returned'],
        expected_return_date__isnull=False,
        expected_return_date__lt=now
    ).count()
    red_total_count = GatePass.objects.filter(card_type='RED').count()

    return render(request, 'gatepass/list.html', {
        'passes': queryset[:100],
        'card_filter': card_filter,
        'status_filter': status_filter,
        'q': q,
        'green_active_count': green_active_count,
        'green_overdue_count': green_overdue_count,
        'red_total_count': red_total_count,
    })

@login_required
def gatepass_create(request):
    departments = DepartmentHost.objects.all().order_by('name')
    initial_card = request.GET.get('type', 'GREEN').upper()
    if initial_card not in ('GREEN', 'RED'):
        initial_card = 'GREEN'

    if request.method == 'POST':
        card_type = request.POST.get('card_type', 'GREEN')
        physical_card_ref = request.POST.get('physical_card_ref', '').strip()
        
        dept_id = request.POST.get('from_department')
        from_dept = DepartmentHost.objects.filter(pk=dept_id).first() if dept_id else None
        sender_name = request.POST.get('sender_name', '').strip()
        sender_email = request.POST.get('sender_email', '').strip()
        sender_phone = request.POST.get('sender_phone', '').strip()

        destination_entity = request.POST.get('destination_entity', '').strip()
        destination_address = request.POST.get('destination_address', '').strip()
        destination_contact_name = request.POST.get('destination_contact_name', '').strip()
        destination_phone = request.POST.get('destination_phone', '').strip()

        carrier_name = request.POST.get('carrier_name', '').strip()
        carrier_phone = request.POST.get('carrier_phone', '').strip()
        carrier_id_number = request.POST.get('carrier_id_number', '').strip()
        carrier_company = request.POST.get('carrier_company', '').strip()
        vehicle_plate = request.POST.get('vehicle_plate', '').strip()
        vehicle_model = request.POST.get('vehicle_model', '').strip()

        purpose = request.POST.get('purpose', 'repair')
        purpose_notes = request.POST.get('purpose_notes', '').strip()
        authorized_by_manager = request.POST.get('authorized_by_manager', '').strip()
        gate_id = request.POST.get('gate_id')
        gate_obj = SecurityGate.objects.filter(pk=gate_id).first() if gate_id else None
        if not gate_obj and request.session.get('current_gate_id'):
            gate_obj = SecurityGate.objects.filter(pk=request.session.get('current_gate_id')).first()
        gate_location = gate_obj.name if gate_obj else request.POST.get('gate_location', 'Loading Dock Gate')

        # Return date calculation
        expected_return_date = None
        if card_type == 'GREEN':
            days_loan = int(request.POST.get('return_days', 7))
            expected_return_date = timezone.now() + timezone.timedelta(days=days_loan)

        gate_pass = GatePass.objects.create(
            card_type=card_type,
            physical_card_ref=physical_card_ref,
            gate=gate_obj,
            from_department=from_dept,
            sender_name=sender_name,
            sender_email=sender_email,
            sender_phone=sender_phone,
            destination_entity=destination_entity,
            destination_address=destination_address,
            destination_contact_name=destination_contact_name,
            destination_phone=destination_phone,
            carrier_name=carrier_name,
            carrier_phone=carrier_phone,
            carrier_id_number=carrier_id_number,
            carrier_company=carrier_company,
            vehicle_plate=vehicle_plate,
            vehicle_model=vehicle_model,
            purpose=purpose,
            purpose_notes=purpose_notes,
            authorized_by_manager=authorized_by_manager,
            gate_location=gate_location,
            expected_return_date=expected_return_date,
            dispatched_by=request.user,
            dispatched_at=timezone.now(),
            status='active' if card_type == 'GREEN' else 'dispatched_closed'
        )

        if 'exit_cargo_photo' in request.FILES:
            gate_pass.exit_cargo_photo = request.FILES['exit_cargo_photo']
            gate_pass.save()

        # Parse Cart Items
        item_names = request.POST.getlist('item_name[]')
        quantities = request.POST.getlist('quantity[]')
        units = request.POST.getlist('unit[]')
        serials = request.POST.getlist('serial_asset_tag[]')
        conditions = request.POST.getlist('condition_out[]')

        for idx, name in enumerate(item_names):
            if name.strip():
                qty = int(quantities[idx]) if idx < len(quantities) and quantities[idx].isdigit() else 1
                u = units[idx] if idx < len(units) else 'pcs'
                s = serials[idx] if idx < len(serials) else ''
                c = conditions[idx] if idx < len(conditions) else 'for_repair'
                GatePassItem.objects.create(
                    pass_card=gate_pass,
                    item_name=name.strip(),
                    quantity=qty,
                    unit=u,
                    serial_asset_tag=s.strip(),
                    condition_out=c,
                )

        # Audit Log
        action_name = 'CHECK_OUT' if card_type == 'GREEN' else 'SECURITY_ALERT'
        card_label = "Green Card (Returnable)" if card_type == 'GREEN' else "Red Card (Non-Returnable)"
        SecurityAuditLog.objects.create(
            user=request.user,
            action=action_name,
            reference=gate_pass.pass_number,
            details=f"Dispatched {card_label} to {destination_entity}. Carrier: {carrier_name}. Items: {gate_pass.total_items_count}.",
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        messages.success(request, f"{card_label} pass {gate_pass.pass_number} created and authorized at gate!")
        return redirect('gatepass_detail', pk=gate_pass.pk)

    return render(request, 'gatepass/create.html', {
        'departments': departments,
        'initial_card': initial_card,
    })

@login_required
def gatepass_detail(request, pk):
    pass_card = get_object_or_404(GatePass.objects.select_related('from_department', 'dispatched_by', 'received_by').prefetch_related('items'), pk=pk)
    return render(request, 'gatepass/detail.html', {'pass_card': pass_card})

@login_required
def gatepass_return(request, pk):
    pass_card = get_object_or_404(GatePass, pk=pk)
    if not pass_card.is_green_card:
        messages.error(request, "Only Green Cards (Returnable Material Passes) require inward return.")
        return redirect('gatepass_detail', pk=pass_card.pk)

    if request.method == 'POST':
        all_returned = True
        for item in pass_card.items.all():
            returned_qty_str = request.POST.get(f'qty_{item.id}', '0')
            returned_qty = int(returned_qty_str) if returned_qty_str.isdigit() else 0
            condition_ret = request.POST.get(f'condition_{item.id}', 'repaired')
            
            item.quantity_returned = returned_qty
            item.condition_returned = condition_ret
            item.is_returned = (returned_qty >= item.quantity)
            item.save()

            if not item.is_returned:
                all_returned = False

        if 'return_cargo_photo' in request.FILES:
            pass_card.return_cargo_photo = request.FILES['return_cargo_photo']

        pass_card.actual_return_date = timezone.now()
        pass_card.received_by = request.user
        pass_card.status = 'fully_returned' if all_returned else 'partially_returned'
        
        notes = request.POST.get('return_notes', '').strip()
        if notes:
            pass_card.security_notes = (pass_card.security_notes + f"\n[{timezone.now().strftime('%d-%b %H:%M')}] Return: {notes}").strip()
        pass_card.save()

        # Audit log
        SecurityAuditLog.objects.create(
            user=request.user,
            action='CHECK_IN',
            reference=pass_card.pass_number,
            details=f"Inward Gate Handover: {pass_card.pass_number} marked {pass_card.get_status_display()}. Received by {request.user.get_full_name() or request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        messages.success(request, f"Gate return processed for {pass_card.pass_number}! Status: {pass_card.get_status_display()}")
        return redirect('gatepass_detail', pk=pass_card.pk)

    return render(request, 'gatepass/return.html', {'pass_card': pass_card})

@login_required
def gatepass_print(request, pk):
    pass_card = get_object_or_404(GatePass.objects.select_related('from_department', 'dispatched_by').prefetch_related('items'), pk=pk)
    return render(request, 'gatepass/print.html', {'pass_card': pass_card})
