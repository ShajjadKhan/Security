from django.db import models
from django.contrib.auth.models import AbstractUser

class SecurityGate(models.Model):
    GATE_TYPE_CHOICES = [
        ('service', 'Loading Dock & Service / رصيف التحميل والخدمات'),
        ('main', 'Main Gate & Barrier / البوابة الرئيسية والحاجز الأمني'),
        ('staff', 'Staff & Contractor Entrance / مدخل الموظفين والمقاولين'),
        ('basement', 'Basement Ramp & Parking / قبو الخدمات والمواقف'),
        ('vip', 'VIP / Protocol Gate / بوابة كبار الشخصيات والبروتوكول'),
    ]
    name = models.CharField(max_length=100, help_text="e.g. Gate 1 - Loading Dock")
    name_ar = models.CharField(max_length=100, blank=True, help_text="e.g. بوابة 1 - رصيف التحميل")
    code = models.CharField(max_length=30, unique=True, help_text="e.g. GATE-01")
    gate_type = models.CharField(max_length=20, choices=GATE_TYPE_CHOICES, default='service')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        display_name = f"{self.name_ar} ({self.name})" if self.name_ar else self.name
        return f"{self.code} - {display_name}"

    def get_localized_name(self, lang='en'):
        if lang == 'ar' and self.name_ar:
            return self.name_ar
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('director', 'Chief of Security / Director'),
        ('supervisor', 'Shift Supervisor'),
        ('officer', 'Security Officer / Gate Guard'),
        ('front_desk', 'Front Desk / Concierge'),
        ('auditor', 'Safety & Auditor'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='officer')
    badge_number = models.CharField(max_length=50, blank=True, null=True, help_text="Officer Employee / Security ID")
    phone = models.CharField(max_length=30, blank=True, null=True)
    shift = models.CharField(max_length=20, choices=[
        ('morning', 'Morning Shift (07:00 - 15:00)'),
        ('afternoon', 'Afternoon Shift (15:00 - 23:00)'),
        ('night', 'Night Shift (23:00 - 07:00)')
    ], default='morning')
    assigned_gate = models.ForeignKey(SecurityGate, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_officers')
    is_on_duty = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class SecurityAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CHECK_IN', 'Visitor Checked In'),
        ('CHECK_OUT', 'Visitor Checked Out'),
        ('VISITOR_DENIED', 'Visitor Entry Denied'),
        ('LF_LOGGED', 'Lost & Found Item Logged'),
        ('LF_CLAIMED', 'Lost & Found Item Handed Over'),
        ('LF_DISPOSED', 'Lost & Found Item Disposed'),
        ('SECURITY_ALERT', 'Security Incident Flagged'),
        ('GATE_ADDED', 'New Security Gate Created'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    gate = models.ForeignKey(SecurityGate, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at}] {self.action} - {self.reference}"
