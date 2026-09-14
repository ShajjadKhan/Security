from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from .models import LostFoundItem, ItemPhoto
from core.models import Property, SecurityAuditLog

@login_required
def lostfound_list(request):
    status_filter = request.GET.get('status', 'all')
    cat_filter = request.GET.get('category', 'all')
    tier_filter = request.GET.get('tier', 'all')
    q = request.GET.get('q', '').strip()
    
    queryset = LostFoundItem.objects.select_related('logged_by', 'released_by').all()
    current_prop_id = request.session.get('current_property_id')
    if current_prop_id and current_prop_id != 'ALL':
        queryset = queryset.filter(property_id=current_prop_id)
    
    if status_filter != 'all':
        queryset = queryset.filter(status=status_filter)
    if cat_filter != 'all':
        queryset = queryset.filter(category=cat_filter)
    if tier_filter != 'all':
        queryset = queryset.filter(value_tier=tier_filter)
        
    if q:
        queryset = queryset.filter(
            Q(reference_number__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__icontains=q) |
            Q(serial_number__icontains=q) |
            Q(found_location__icontains=q) |
            Q(finder_name__icontains=q) |
            Q(claimant_name__icontains=q)
        )
        
    return render(request, 'lostfound/list.html', {
        'items': queryset[:100],
        'status_filter': status_filter,
        'cat_filter': cat_filter,
        'tier_filter': tier_filter,
        'q': q,
    })

@login_required
def lostfound_create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        category = request.POST.get('category', 'electronics')
        value_tier = request.POST.get('value_tier', 'normal')
        description = request.POST.get('description', '').strip()
        brand = request.POST.get('brand', '').strip()
        color = request.POST.get('color', '').strip()
        serial_number = request.POST.get('serial_number', '').strip()
        
        found_location = request.POST.get('found_location', '').strip()
        finder_name = request.POST.get('finder_name', '').strip()
        finder_type = request.POST.get('finder_type', 'staff')
        finder_phone = request.POST.get('finder_phone', '').strip()
        storage_location = request.POST.get('storage_location', 'Security Safe').strip()
        
        current_prop_id = request.session.get('current_property_id')
        current_prop = None
        if current_prop_id and current_prop_id != 'ALL':
            current_prop = Property.objects.filter(id=current_prop_id).first()
        elif not current_prop_id:
            current_prop = getattr(request.user, 'assigned_property', None) or Property.objects.filter(is_active=True).first()

        item = LostFoundItem.objects.create(
            property=current_prop,
            title=title,
            category=category,
            value_tier=value_tier,
            description=description,
            brand=brand,
            color=color,
            serial_number=serial_number,
            found_location=found_location,
            finder_name=finder_name,
            finder_type=finder_type,
            finder_phone=finder_phone,
            storage_location=storage_location,
            logged_by=request.user,
            status='unclaimed',
        )
        
        if 'primary_photo' in request.FILES:
            item.primary_photo = request.FILES['primary_photo']
            item.save()
            
        # Additional gallery photos
        extra_photos = request.FILES.getlist('extra_photos')
        for p in extra_photos:
            ItemPhoto.objects.create(item=item, photo=p)
            
        SecurityAuditLog.objects.create(
            user=request.user,
            action='LF_LOGGED',
            reference=item.reference_number,
            details=f"Logged {item.title} ({item.get_category_display()}) found at {item.found_location} by {finder_name or finder_type}. Storage: {item.storage_location}",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(request, f"Item registered in Lost & Found custody! Reference: {item.reference_number}")
        return redirect('lostfound_detail', pk=item.pk)
        
    return render(request, 'lostfound/create.html')

@login_required
def lostfound_detail(request, pk):
    item = get_object_or_404(LostFoundItem.objects.select_related('logged_by', 'released_by').prefetch_related('photos'), pk=pk)
    return render(request, 'lostfound/detail.html', {'item': item})

@login_required
def lostfound_claim(request, pk):
    item = get_object_or_404(LostFoundItem, pk=pk)
    
    if request.method == 'POST':
        claimant_name = request.POST.get('claimant_name', '').strip()
        claimant_phone = request.POST.get('claimant_phone', '').strip()
        claimant_id_number = request.POST.get('claimant_id_number', '').strip()
        proof_of_ownership = request.POST.get('proof_of_ownership', '').strip()
        handover_notes = request.POST.get('handover_notes', '').strip()
        
        item.status = 'claimed'
        item.claimant_name = claimant_name
        item.claimant_phone = claimant_phone
        item.claimant_id_number = claimant_id_number
        item.proof_of_ownership = proof_of_ownership
        item.handover_notes = handover_notes
        item.handover_date = timezone.now()
        item.released_by = request.user
        
        if 'claimant_signature_photo' in request.FILES:
            item.claimant_signature_photo = request.FILES['claimant_signature_photo']
        item.save()
        
        SecurityAuditLog.objects.create(
            user=request.user,
            action='LF_CLAIMED',
            reference=item.reference_number,
            details=f"Item {item.reference_number} ({item.title}) returned to {claimant_name} (ID: {claimant_id_number}). Released by {request.user.get_full_name() or request.user.username}.",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        
        messages.success(request, f"Item {item.reference_number} successfully claimed and handed over to {claimant_name}!")
        return redirect('lostfound_detail', pk=item.pk)
        
    return render(request, 'lostfound/claim.html', {'item': item})
