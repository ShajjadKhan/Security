import random
from django.db import models
from django.utils import timezone
from core.models import User

def generate_lf_ref():
    date_str = timezone.now().strftime('%y%m%d')
    rand = ''.join(random.choices('0123456789', k=4))
    return f"LF-{date_str}-{rand}"

class LostFoundItem(models.Model):
    CATEGORY_CHOICES = [
        ('electronics', 'Electronics (Phones, Laptops, Earbuds, Chargers, Cameras)'),
        ('wallet_cash', 'Wallets, Purses & Cash'),
        ('jewelry', 'Jewelry, Watches & Luxury Goods'),
        ('documents', 'Passports, IDs, Bank Cards & Keys'),
        ('luggage_bags', 'Baggage, Backpacks & Briefcases'),
        ('clothing', 'Clothing, Eyewear & Shoes'),
        ('accessories', 'Hats, Umbrellas, Personal Items'),
        ('other', 'Other Miscellaneous Items'),
    ]
    STATUS_CHOICES = [
        ('unclaimed', 'Unclaimed (In Custody)'),
        ('investigating', 'Claim In Verification'),
        ('claimed', 'Claimed & Returned'),
        ('disposed', 'Disposed / Discarded'),
        ('donated', 'Donated to Charity'),
        ('police', 'Transferred to Police / Authorities'),
    ]
    VALUE_TIER_CHOICES = [
        ('normal', 'Standard Item'),
        ('high_value', 'High Value (Safe Custody Required)'),
        ('sensitive', 'Confidential / Sensitive Documents / Cash'),
    ]

    reference_number = models.CharField(max_length=30, unique=True, default=generate_lf_ref, editable=False)
    title = models.CharField(max_length=150, help_text="Short title e.g. Silver iPhone 15 Pro, Black Montblanc Wallet")
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='electronics')
    value_tier = models.CharField(max_length=20, choices=VALUE_TIER_CHOICES, default='normal')
    description = models.TextField(help_text="Detailed physical description, condition, distinguishing marks, scratches, lock-screen wallpaper, serial numbers")
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=100, blank=True, help_text="IMEI, serial number, or card ending digits")
    
    # Discovery Info
    found_location = models.CharField(max_length=150, help_text="e.g. Main Lobby Couch, Room 412, Restaurant Table 8, Gym")
    found_date = models.DateTimeField(default=timezone.now)
    finder_name = models.CharField(max_length=100, blank=True)
    finder_type = models.CharField(max_length=30, choices=[
        ('staff', 'Hotel Staff Member'),
        ('guest', 'Hotel Guest / Visitor'),
        ('security', 'Security Officer / Patrol'),
        ('contractor', 'Contractor / Vendor')
    ], default='staff')
    finder_phone = models.CharField(max_length=30, blank=True)

    # Custody & Storage
    storage_location = models.CharField(max_length=100, default='Security Main Safe', help_text="e.g. Safe Box A, Locker #14, Shelf 2")
    logged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='items_logged')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unclaimed')

    # Primary Photo
    primary_photo = models.ImageField(upload_to='lostfound_photos/', blank=True, null=True)

    # Claim & Handover Info
    claimant_name = models.CharField(max_length=150, blank=True)
    claimant_phone = models.CharField(max_length=30, blank=True)
    claimant_id_number = models.CharField(max_length=50, blank=True)
    proof_of_ownership = models.TextField(blank=True, help_text="How claimant proved ownership: passcode entry, receipt, invoice, hidden mark")
    handover_date = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='items_released')
    claimant_signature_photo = models.ImageField(upload_to='claim_signatures/', blank=True, null=True)
    handover_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def days_in_custody(self):
        end = self.handover_date or timezone.now()
        return (end - self.found_date).days

    def __str__(self):
        return f"{self.reference_number} - {self.title} ({self.get_status_display()})"


class ItemPhoto(models.Model):
    item = models.ForeignKey(LostFoundItem, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='lostfound_photos/gallery/')
    caption = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
