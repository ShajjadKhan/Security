from django.db import models
from django.contrib.auth.models import AbstractUser

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
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    reference = models.CharField(max_length=100, blank=True)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at}] {self.action} - {self.reference}"
