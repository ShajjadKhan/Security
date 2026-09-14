from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from visitors.models import Visitor, DepartmentHost
from lostfound.models import LostFoundItem
from .models import User, SecurityAuditLog

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        u = request.POST.get('username', '').strip()
        p = request.POST.get('password', '').strip()
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
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
    
    # Live KPI counts
    active_visitors = Visitor.objects.filter(status='active').select_related('host_department', 'checked_in_by')
    active_count = active_visitors.count()
    
    today_checkins = Visitor.objects.filter(check_in_time__gte=today_start).count()
    today_checkouts = Visitor.objects.filter(check_out_time__gte=today_start).count()
    
    overstay_visitors = Visitor.objects.filter(
        status='active',
        expected_checkout_time__isnull=False,
        expected_checkout_time__lt=now
    )
    overstay_count = overstay_visitors.count()

    # Lost & Found metrics
    unclaimed_lf = LostFoundItem.objects.filter(status='unclaimed')
    unclaimed_count = unclaimed_lf.count()
    high_value_count = unclaimed_lf.filter(value_tier='high_value').count()
    today_lf_logged = LostFoundItem.objects.filter(created_at__gte=today_start).count()

    # Recent activity
    recent_visitors = Visitor.objects.all()[:8]
    recent_lostfound = LostFoundItem.objects.all()[:6]
    recent_audits = SecurityAuditLog.objects.all()[:10]

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
    }
    return render(request, 'dashboard.html', context)

@login_required
def audit_log_view(request):
    logs = SecurityAuditLog.objects.select_related('user').all()[:200]
    return render(request, 'audit_log.html', {'logs': logs})

@login_required
def universal_search_view(request):
    q = request.GET.get('q', '').strip()
    visitors = []
    lostfound_items = []
    
    if q:
        visitors = Visitor.objects.filter(
            Q(full_name__icontains=q) |
            Q(pass_number__icontains=q) |
            Q(phone__icontains=q) |
            Q(id_number__icontains=q) |
            Q(vehicle_plate__icontains=q) |
            Q(company_name__icontains=q)
        )[:20]
        
        lostfound_items = LostFoundItem.objects.filter(
            Q(reference_number__icontains=q) |
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(brand__icontains=q) |
            Q(serial_number__icontains=q) |
            Q(found_location__icontains=q) |
            Q(claimant_name__icontains=q)
        )[:20]
        
    return render(request, 'search_results.html', {
        'q': q,
        'visitors': visitors,
        'lostfound_items': lostfound_items,
    })
