from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import Visitor, DepartmentHost
from core.models import Property, SecurityGate, SecurityAuditLog
from core.utils import is_safe_image

def accessible_properties_for(user):
    if hasattr(user, 'get_accessible_properties'):
        return user.get_accessible_properties()
    return Property.objects.none()

@login_required
def visitor_list(request):
    status_filter = request.GET.get('status', 'all')
    cat_filter = request.GET.get('category', 'all')
    q = request.GET.get('q', '').strip()
    
    accessible_properties = accessible_properties_for(request.user)
    queryset = Visitor.objects.select_related('host_department', 'checked_in_by').filter(property__in=accessible_properties)
    current_prop_id = request.session.get('current_property_id')
    if current_prop_id and current_prop_id != 'ALL':
        queryset = queryset.filter(property_id=current_prop_id)
    
    if status_filter == 'active':
        queryset = queryset.filter(status='active')
    elif status_filter == 'overstay':
        queryset = queryset.filter(
            status='active',
            expected_checkout_time__isnull=False,
            expected_checkout_time__lt=timezone.now()
        )
    elif status_filter == 'checked_out':
        queryset = queryset.filter(status='checked_out')
        
    if cat_filter != 'all':
        queryset = queryset.filter(category=cat_filter)
        
    if q:
        queryset = queryset.filter(
            Q(full_name__icontains=q) |
            Q(pass_number__icontains=q) |
            Q(phone__icontains=q) |
            Q(id_number__icontains=q) |
            Q(vehicle_plate__icontains=q) |
            Q(company_name__icontains=q)
        )
        
    return render(request, 'visitors/list.html', {
        'visitors': queryset[:100],
        'status_filter': status_filter,
        'cat_filter': cat_filter,
        'q': q,
    })

@login_required
def visitor_checkin(request):
    accessible_properties = accessible_properties_for(request.user)
    departments = DepartmentHost.objects.filter(property__in=accessible_properties).order_by('name')
    
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        category = request.POST.get('category', 'guest')
        company_name = request.POST.get('company_name', '').strip()
        id_type = request.POST.get('id_type', 'national_id')
        id_number = request.POST.get('id_number', '').strip()
        
        dept_id = request.POST.get('host_department')
        host_dept = departments.filter(pk=dept_id).first() if dept_id else None
        host_person = request.POST.get('host_person', '').strip()
        purpose = request.POST.get('purpose', '').strip()
        
        has_vehicle = request.POST.get('has_vehicle') == 'on'
        vehicle_plate = request.POST.get('vehicle_plate', '').strip()
        vehicle_model = request.POST.get('vehicle_model', '').strip()
        parking_slot = request.POST.get('parking_slot', '').strip()
        tools_declared = request.POST.get('tools_declared', '').strip()
        gate_location = request.POST.get('gate_location', 'Main Gate')
        expected_hours = int(request.POST.get('expected_hours', 2))
        
        expected_checkout = timezone.now() + timezone.timedelta(hours=expected_hours)
        
        current_prop_id = request.session.get('current_property_id')
        current_prop = None
        if current_prop_id and current_prop_id != 'ALL':
            current_prop = accessible_properties.filter(id=current_prop_id).first()
        elif not current_prop_id:
            current_prop = getattr(request.user, 'assigned_property', None) if getattr(request.user, 'assigned_property', None) in accessible_properties else accessible_properties.first()
        elif current_prop_id == 'ALL':
            current_prop = accessible_properties.first()

        current_gate_id = request.session.get('current_gate_id')
        current_gate = SecurityGate.objects.filter(property__in=accessible_properties, id=current_gate_id).first() if current_gate_id else getattr(request.user, 'assigned_gate', None)

        visitor = Visitor.objects.create(
            property=current_prop,
            gate=current_gate,
            full_name=full_name,
            phone=phone,
            category=category,
            company_name=company_name,
            id_type=id_type,
            id_number=id_number,
            host_department=host_dept,
            host_person=host_person,
            purpose=purpose,
            has_vehicle=has_vehicle,
            vehicle_plate=vehicle_plate,
            vehicle_model=vehicle_model,
            parking_slot=parking_slot,
            tools_declared=tools_declared,
            gate_location=gate_location,
            checked_in_by=request.user,
            expected_checkout_time=expected_checkout,
            status='active',
        )
        
        if 'id_photo' in request.FILES:
            photo = request.FILES['id_photo']
            if is_safe_image(photo):
                visitor.id_photo = photo
        if 'visitor_photo' in request.FILES:
            photo = request.FILES['visitor_photo']
            if is_safe_image(photo):
                visitor.visitor_photo = photo
        visitor.save()
        
        # Log audit
        SecurityAuditLog.objects.create(
            user=request.user,
            property=visitor.property,
            gate=visitor.gate,
            action='CHECK_IN',
            reference=visitor.pass_number,
            details=f"Checked in {visitor.full_name} ({visitor.get_category_display()}) at {visitor.gate_location}. Host: {host_person or (host_dept.name if host_dept else 'General')}",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(request, f"Visitor checked in successfully! Pass generated: {visitor.pass_number}")
        return redirect('visitor_pass_print', pk=visitor.pk)
        
    return render(request, 'visitors/checkin.html', {
        'departments': departments,
    })

@login_required
def visitor_detail(request, pk):
    visitor = get_object_or_404(Visitor.objects.filter(property__in=accessible_properties_for(request.user)).select_related('host_department', 'checked_in_by', 'checked_out_by'), pk=pk)
    return render(request, 'visitors/detail.html', {'visitor': visitor})

@login_required
def visitor_checkout(request, pk):
    visitor = get_object_or_404(Visitor.objects.filter(property__in=accessible_properties_for(request.user)), pk=pk)
    if visitor.status != 'checked_out':
        visitor.status = 'checked_out'
        visitor.check_out_time = timezone.now()
        visitor.checked_out_by = request.user
        visitor.badge_returned = True
        notes = request.POST.get('checkout_notes', '').strip()
        if notes:
            visitor.security_notes = (visitor.security_notes + f"\n[{timezone.now().strftime('%H:%M')}] Checkout: {notes}").strip()
        visitor.save()
        
        SecurityAuditLog.objects.create(
            user=request.user,
            property=visitor.property,
            gate=visitor.gate,
            action='CHECK_OUT',
            reference=visitor.pass_number,
            details=f"Checked out {visitor.full_name}. Duration: {visitor.duration_formatted}. Badge returned.",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        messages.success(request, f"{visitor.full_name} ({visitor.pass_number}) successfully checked out!")
    else:
        messages.info(request, f"{visitor.full_name} was already checked out.")
        
    next_url = request.POST.get('next') or request.GET.get('next') or 'visitor_list'
    return redirect(next_url)

@login_required
def visitor_pass_print(request, pk):
    visitor = get_object_or_404(Visitor.objects.filter(property__in=accessible_properties_for(request.user)).select_related('host_department', 'checked_in_by'), pk=pk)
    return render(request, 'visitors/pass_print.html', {'visitor': visitor})
