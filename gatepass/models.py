import random
import urllib.parse
from django.db import models
from django.utils import timezone
from core.models import User
from visitors.models import DepartmentHost

def generate_pass_number(card_type):
    prefix = "GC" if card_type == 'GREEN' else "RC"
    date_str = timezone.now().strftime('%y%m%d')
    rand = ''.join(random.choices('0123456789', k=4))
    return f"{prefix}-{date_str}-{rand}"

class GatePass(models.Model):
    CARD_TYPE_CHOICES = [
        ('GREEN', '🟢 Green Card — Returnable Material Pass (MUST RETURN)'),
        ('RED', '🔴 Red Card — Non-Returnable Material Pass (PERMANENT OUT)'),
    ]

    STATUS_CHOICES = [
        ('active', 'Out In-Transit'),
        ('overdue', 'Overdue for Return'),
        ('partially_returned', 'Partially Returned'),
        ('fully_returned', 'Fully Returned & Closed'),
        ('dispatched_closed', 'Dispatched & Closed (Permanent Out)'),
        ('cancelled', 'Cancelled'),
    ]

    PURPOSE_CHOICES = [
        ('repair', 'External Repair & Servicing'),
        ('calibration', 'Calibration & Testing'),
        ('warranty', 'Warranty Replacement / Vendor Return'),
        ('inter_branch', 'Inter-Branch / Sister Hotel Transfer'),
        ('demo', 'Exhibition / Demonstration / Event Loan'),
        ('scrap', 'Scrap Disposal / Recycling Waste'),
        ('donation_sale', 'Sold Surplus / Donated Asset'),
        ('guest_property', 'Guest Property Dispatched / Courier'),
        ('other', 'Other Authorized Purpose'),
    ]

    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES, default='GREEN')
    pass_number = models.CharField(max_length=30, unique=True, editable=False)
    physical_card_ref = models.CharField(max_length=50, blank=True, help_text="Optional physical plastic card / badge number (e.g. Card #12)")

    # 1. Origin (From)
    from_department = models.ForeignKey(DepartmentHost, on_delete=models.SET_NULL, null=True, related_name='gate_passes_sent')
    sender_name = models.CharField(max_length=120, help_text="Department staff member dispatching the items")
    sender_email = models.EmailField(blank=True, help_text="Email for departure receipt and return notifications")
    sender_phone = models.CharField(max_length=30, blank=True, help_text="Department phone / WhatsApp")

    # 2. Destination (To)
    destination_entity = models.CharField(max_length=150, help_text="Company, workshop, vendor, or recipient facility")
    destination_address = models.CharField(max_length=200, blank=True)
    destination_contact_name = models.CharField(max_length=120, blank=True)
    destination_phone = models.CharField(max_length=30, blank=True)
    destination_email = models.EmailField(blank=True)

    # 3. Carrier (Who is taking it)
    carrier_name = models.CharField(max_length=120, help_text="Driver or employee physically transporting the items")
    carrier_phone = models.CharField(max_length=30, help_text="Mobile number for WhatsApp reminders")
    carrier_id_number = models.CharField(max_length=50, blank=True, help_text="National ID / Iqama / License")
    carrier_company = models.CharField(max_length=120, blank=True, help_text="Transport company or logistics service")
    vehicle_plate = models.CharField(max_length=30, blank=True, help_text="e.g. KSA 4921 RKD")
    vehicle_model = models.CharField(max_length=60, blank=True, help_text="e.g. White Isuzu Truck")

    # 4. Purpose (Why)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default='repair')
    purpose_notes = models.TextField(blank=True, help_text="Detailed justification of movement")

    # 5. Authorization & Verification
    authorized_by_manager = models.CharField(max_length=120, help_text="Department Head or Director who signed approval")
    approval_document_photo = models.ImageField(upload_to='gatepass_approvals/', blank=True, null=True)

    # 6. Gate Security Operations
    dispatched_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='passes_dispatched')
    created_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(default=timezone.now)
    gate = models.ForeignKey('core.SecurityGate', on_delete=models.SET_NULL, null=True, blank=True, related_name='gate_passes')
    gate_location = models.CharField(max_length=100, default='Loading Dock Gate')
    exit_cargo_photo = models.ImageField(upload_to='gatepass_cargo_exit/', blank=True, null=True)

    # 7. Timestamps & Return Flow (Green Card)
    expected_return_date = models.DateTimeField(null=True, blank=True, help_text="Mandatory return cutoff for Green Cards")
    actual_return_date = models.DateTimeField(null=True, blank=True)
    received_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='passes_returned')
    return_cargo_photo = models.ImageField(upload_to='gatepass_cargo_return/', blank=True, null=True)
    
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='active')
    security_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.pass_number:
            self.pass_number = generate_pass_number(self.card_type)
        if self.card_type == 'RED' and self.status == 'active':
            self.status = 'dispatched_closed'
        super().save(*args, **kwargs)

    @property
    def is_green_card(self):
        return self.card_type == 'GREEN'

    @property
    def is_red_card(self):
        return self.card_type == 'RED'

    @property
    def is_overdue(self):
        if self.is_green_card and self.status in ('active', 'partially_returned') and self.expected_return_date:
            return timezone.now() > self.expected_return_date
        return False

    @property
    def days_overdue(self):
        if self.is_overdue:
            return (timezone.now() - self.expected_return_date).days
        return 0

    @property
    def time_remaining_display(self):
        if not self.expected_return_date:
            return "N/A (Permanent)"
        now = timezone.now()
        if now > self.expected_return_date:
            delta = now - self.expected_return_date
            return f"OVERDUE by {delta.days}d {delta.seconds//3600}h"
        delta = self.expected_return_date - now
        return f"{delta.days}d {delta.seconds//3600}h remaining"

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def whatsapp_carrier_url(self):
        if not self.carrier_phone:
            return ""
        clean_phone = self.carrier_phone.replace('+', '').replace(' ', '').replace('-', '')
        items_summary = ", ".join([f"{i.quantity}x {i.item_name}" for i in self.items.all()[:3]])
        if self.items.count() > 3:
            items_summary += "..."
        
        return_str = self.expected_return_date.strftime('%d-%b-%Y %H:%M') if self.expected_return_date else "N/A"
        msg = (
            f"🛡️ *SECURITY DEPARTMENT GATE PASS NOTICE*\n\n"
            f"Pass Number: *{self.pass_number}* (Green Card)\n"
            f"Items: {items_summary}\n"
            f"Destination: {self.destination_entity}\n"
            f"Expected Return Date: *{return_str}*\n\n"
            f"Dear {self.carrier_name}, please ensure all items are returned to Security Gate before the deadline.\n"
            f"Gate Hotline: +966 50 000 0000"
        )
        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{clean_phone}?text={encoded}"

    @property
    def whatsapp_dept_url(self):
        if not self.sender_phone:
            return ""
        clean_phone = self.sender_phone.replace('+', '').replace(' ', '').replace('-', '')
        return_str = self.expected_return_date.strftime('%d-%b-%Y %H:%M') if self.expected_return_date else "N/A"
        msg = (
            f"🛡️ *SECURITY ALERT - OVERDUE MATERIAL PASS*\n\n"
            f"Pass: *{self.pass_number}* (Green Card)\n"
            f"Department: {self.from_department.name if self.from_department else 'General'}\n"
            f"Carrier: {self.carrier_name} ({self.carrier_phone})\n"
            f"Destination: {self.destination_entity}\n"
            f"Due Date was: *{return_str}*\n\n"
            f"Please coordinate return of these assets to Security Gate."
        )
        encoded = urllib.parse.quote(msg)
        return f"https://wa.me/{clean_phone}?text={encoded}"

    def __str__(self):
        return f"[{self.card_type}] {self.pass_number} - {self.destination_entity}"


class GatePassItem(models.Model):
    pass_card = models.ForeignKey(GatePass, on_delete=models.CASCADE, related_name='items')
    item_name = models.CharField(max_length=150, help_text="e.g. Chiller Water Pump, Dining Chairs, Drill Press")
    quantity = models.PositiveIntegerField(default=1)
    unit = models.CharField(max_length=30, default='pcs', help_text="pcs, sets, boxes, kg, meters")
    serial_asset_tag = models.CharField(max_length=100, blank=True, help_text="Serial number or asset tag e.g. ASSET-ENG-4910")
    condition_out = models.CharField(max_length=30, choices=[
        ('good', 'Good Working Condition'),
        ('for_repair', 'Faulty / Sent for Repair'),
        ('damaged', 'Damaged / Scrap Material'),
    ], default='for_repair')
    
    # Return Tracking (Green Card)
    quantity_returned = models.PositiveIntegerField(default=0)
    condition_returned = models.CharField(max_length=30, blank=True, choices=[
        ('repaired', 'Repaired & Fully Working'),
        ('same', 'Same Condition (Unchanged)'),
        ('damaged', 'Beyond Repair / Returned Damaged'),
    ])
    is_returned = models.BooleanField(default=False)
    item_photo = models.ImageField(upload_to='gatepass_items/', blank=True, null=True)

    def __str__(self):
        return f"{self.quantity} {self.unit} x {self.item_name}"
