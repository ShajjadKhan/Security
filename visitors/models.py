import builtins
import random
from django.db import models
from django.utils import timezone
from core.models import User

def generate_pass_number():
    date_str = timezone.now().strftime('%y%m%d')
    rand = ''.join(random.choices('0123456789', k=4))
    return f"PASS-{date_str}-{rand}"

class DepartmentHost(models.Model):
    property = models.ForeignKey('core.Property', on_delete=models.CASCADE, null=True, blank=True, related_name='departments')
    name = models.CharField(max_length=100)
    floor_room = models.CharField(max_length=50, blank=True, help_text="e.g. Floor 3 / Room 302 / Admin Office")
    contact_person = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.name} ({self.floor_room})" if self.floor_room else self.name


class Visitor(models.Model):
    CATEGORY_CHOICES = [
        ('guest', 'Guest / Personal Visitor'),
        ('contractor', 'Contractor / Technician / Maintenance'),
        ('delivery', 'Delivery / Courier / Logistics'),
        ('official', 'VIP / Government / Official Inspector'),
        ('interview', 'Interviewee / Job Applicant'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('active', 'On Premises (Checked In)'),
        ('checked_out', 'Checked Out'),
        ('overstay', 'Flagged Overstay'),
        ('denied', 'Entry Denied'),
    ]
    ID_TYPE_CHOICES = [
        ('national_id', 'Saudi National ID'),
        ('iqama', 'Iqama / Resident Permit'),
        ('passport', 'Passport'),
        ('driving_license', 'Driving License'),
        ('company_badge', 'Company Contractor Badge'),
    ]

    pass_number = models.CharField(max_length=30, unique=True, default=generate_pass_number, editable=False)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='guest')
    company_name = models.CharField(max_length=150, blank=True, help_text="Contractor or employer company")
    
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='national_id')
    id_number = models.CharField(max_length=50)
    id_photo = models.ImageField(upload_to='id_photos/', blank=True, null=True)
    visitor_photo = models.ImageField(upload_to='visitor_photos/', blank=True, null=True)

    host_department = models.ForeignKey(DepartmentHost, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    host_person = models.CharField(max_length=100, blank=True, help_text="Staff name, guest name, or room number being visited")
    purpose = models.CharField(max_length=250, help_text="Reason for entry / visit")

    # Vehicle & Equipment
    has_vehicle = models.BooleanField(default=False)
    vehicle_plate = models.CharField(max_length=30, blank=True, help_text="e.g. ABC 1234")
    vehicle_model = models.CharField(max_length=60, blank=True, help_text="e.g. Toyota Hilux, White")
    parking_slot = models.CharField(max_length=30, blank=True)
    tools_declared = models.TextField(blank=True, help_text="Tools, equipment, heavy gear declared at gate")

    # Gate & Timestamps
    gate_location = models.CharField(max_length=50, default='Main Gate', choices=[
        ('Main Gate', 'Main Security Gate'),
        ('Staff Entrance', 'Staff & Service Entrance'),
        ('Loading Dock', 'Loading Dock / Delivery Gate'),
        ('VIP Lobby', 'VIP / Executive Entrance')
    ])
    property = models.ForeignKey('core.Property', on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    gate = models.ForeignKey('core.SecurityGate', on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors')
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='visitors_checked_in')
    check_in_time = models.DateTimeField(default=timezone.now)
    expected_checkout_time = models.DateTimeField(null=True, blank=True)
    
    checked_out_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitors_checked_out')
    check_out_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    badge_returned = models.BooleanField(default=False)
    security_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-check_in_time']
    @builtins.property
    def duration_formatted(self):
        if not self.check_in_time:
            return "0m"
        end = self.check_out_time or timezone.now()
        total_seconds = int((end - self.check_in_time).total_seconds())
        hours = total_seconds // 3600
        mins = (total_seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    @builtins.property
    def is_overstay(self):
        if self.status == 'active' and self.expected_checkout_time:
            return timezone.now() > self.expected_checkout_time
        return False

    def __str__(self):
        return f"{self.pass_number} - {self.full_name} ({self.get_category_display()})"
