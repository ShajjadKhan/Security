from django.db import models
from django.contrib.auth.models import AbstractUser

class Property(models.Model):
    PROPERTY_TYPE_CHOICES = [
        ('hotel', 'Hotel & Luxury Resort / فندق ومنتجع سياحي'),
        ('commercial', 'Commercial Tower & Business Hub / برج تجاري ومجمع أعمال'),
        ('logistics', 'Logistics & Industrial Park / مجمع لوجستي ومستودعات'),
        ('residential', 'Residential Compound / مجمع سكني خاص'),
        ('healthcare', 'Hospital & Medical City / مستشفى ومدينة طبية'),
        ('campus', 'Educational / University Campus / حرم جامعي أو تعليمي'),
        ('mixed_use', 'Mixed-Use Development / مشروع متعدد الاستخدامات'),
    ]
    name = models.CharField(max_length=150, help_text="e.g. Riyadh Grand Palace Hotel")
    name_ar = models.CharField(max_length=150, blank=True, help_text="e.g. فندق قصر الرياض الكبير")
    code = models.CharField(max_length=30, unique=True, help_text="e.g. PROP-RUH-01")
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPE_CHOICES, default='hotel')
    city = models.CharField(max_length=100, default='Riyadh')
    address = models.CharField(max_length=250, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    manager_name = models.CharField(max_length=120, blank=True, help_text="General Manager or Security Director")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # SaaS Subscription & Monthly Fee Attributes (Software Seller / Multi-Tenant Billing)
    PLAN_TIER_CHOICES = [
        ('starter', 'Starter Package / الباقة الأساسية (500 SAR/mo)'),
        ('professional', 'Professional Facility / باقة المنشآت الاحترافية (1,500 SAR/mo)'),
        ('enterprise', 'Enterprise Cluster / باقة المؤسسات والقطاعات (3,500 SAR/mo)'),
    ]
    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly / شهري'),
        ('quarterly', 'Quarterly / ربع سنوي'),
        ('annually', 'Annually / سنوي'),
    ]
    SUBSCRIPTION_STATUS_CHOICES = [
        ('active', 'Active & Paid / نشط ومسدد'),
        ('trial', 'Free Trial / تجريبي'),
        ('past_due', 'Payment Due / متأخر السداد'),
        ('suspended', 'Suspended / موقوف لعدم السداد'),
        ('cancelled', 'Cancelled / ملغي'),
    ]
    plan_tier = models.CharField(max_length=25, choices=PLAN_TIER_CHOICES, default='professional')
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00, help_text="Monthly SaaS subscription fee in SAR")
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLE_CHOICES, default='monthly')
    subscription_status = models.CharField(max_length=25, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')
    next_billing_date = models.DateField(null=True, blank=True)
    buyer_company = models.CharField(max_length=150, blank=True, help_text="Client Organization / Company Name")
    buyer_name = models.CharField(max_length=120, blank=True, help_text="Buyer / Primary Contact Person")
    buyer_phone = models.CharField(max_length=30, blank=True)
    buyer_email = models.EmailField(blank=True)
    subscription_notes = models.TextField(blank=True, help_text="Contract notes, discounts, terms")

    class Meta:
        ordering = ['code']
        verbose_name_plural = 'Properties'

    def __str__(self):
        display_name = f"{self.name_ar} ({self.name})" if self.name_ar else self.name
        return f"[{self.code}] {display_name}"

    @property
    def is_subscription_active(self):
        return self.is_active and self.subscription_status in ('active', 'trial')

    def get_localized_name(self, lang='en'):
        if lang == 'ar' and self.name_ar:
            return self.name_ar
        return self.name


class SecurityGate(models.Model):
    GATE_TYPE_CHOICES = [
        ('service', 'Loading Dock & Service / رصيف التحميل والخدمات'),
        ('main', 'Main Gate & Barrier / البوابة الرئيسية والحاجز الأمني'),
        ('staff', 'Staff & Contractor Entrance / مدخل الموظفين والمقاولين'),
        ('basement', 'Basement Ramp & Parking / قبو الخدمات والمواقف'),
        ('vip', 'VIP / Protocol Gate / بوابة كبار الشخصيات والبروتوكول'),
    ]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, null=True, blank=True, related_name='gates')
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
        prop_str = f"[{self.property.code}] " if self.property else ""
        return f"{prop_str}{self.code} - {display_name}"

    def get_localized_name(self, lang='en'):
        if lang == 'ar' and self.name_ar:
            return self.name_ar
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = [
        ('saas_owner', 'SaaS Platform Owner & Vendor / بائع ومطور النظام'),
        ('director', 'Chief of Security / Director'),
        ('cluster_director', 'Cluster Security Director / مدير أمن القطاع'),
        ('supervisor', 'Shift Supervisor'),
        ('officer', 'Security Officer / Gate Guard'),
        ('front_desk', 'Front Desk / Concierge'),
        ('auditor', 'Safety & Auditor'),
    ]
    role = models.CharField(max_length=25, choices=ROLE_CHOICES, default='officer')
    badge_number = models.CharField(max_length=50, blank=True, null=True, help_text="Officer Employee / Security ID")
    phone = models.CharField(max_length=30, blank=True, null=True)
    shift = models.CharField(max_length=20, choices=[
        ('morning', 'Morning Shift (07:00 - 15:00)'),
        ('afternoon', 'Afternoon Shift (15:00 - 23:00)'),
        ('night', 'Night Shift (23:00 - 07:00)')
    ], default='morning')
    assigned_property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='personnel')
    cluster_properties = models.ManyToManyField(
        Property,
        blank=True,
        related_name='cluster_directors',
        help_text="Cluster properties managed by this Director / Admin (e.g. Property 1, 2, 3, 4)"
    )
    assigned_gate = models.ForeignKey(SecurityGate, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_officers')
    is_on_duty = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_saas_owner(self):
        return self.is_superuser or self.role == 'saas_owner'

    @property
    def is_cluster_director(self):
        """
        True only for client-side Cluster Directors managing multiple assigned properties.
        Super Admin (SaaS Owner) is NOT a cluster director; they are the platform administrator.
        """
        if self.is_superuser or self.role == 'saas_owner':
            return False
        return self.role == 'cluster_director' or (self.role == 'director' and self.cluster_properties.exists())

    def get_accessible_properties(self):
        """
        Returns QuerySet of properties accessible by this user:
        - SaaS Platform Owner / Superusers: All active properties
        - Cluster Director: All properties in their assigned cluster
        - Regular Personnel: Assigned single property
        """
        if self.is_superuser or self.role == 'saas_owner':
            return Property.objects.filter(is_active=True).order_by('code')
        cluster = self.cluster_properties.filter(is_active=True).order_by('code')
        if cluster.exists():
            return cluster
        if self.assigned_property and self.assigned_property.is_active:
            return Property.objects.filter(id=self.assigned_property.id)
        return Property.objects.none()



class SecurityAuditLog(models.Model):
    ACTION_CHOICES = [
        ('CHECK_IN', 'Visitor Checked In'),
        ('CHECK_OUT', 'Visitor Checked Out'),
        ('VISITOR_DENIED', 'Visitor Entry Denied'),
        ('LF_LOGGED', 'Lost & Found Item Logged'),
        ('LF_CLAIMED', 'Lost & Found Item Handed Over'),
        ('LF_DISPOSED', 'Lost & Found Item Disposed'),
        ('SECURITY_ALERT', 'Security Incident Flagged'),
        ('PASS_CREATED', 'Gate Pass Issued / Dispatched'),
        ('PASS_EDITED', 'Gate Pass Modified / Updated'),
        ('PASS_DELETED', 'Gate Pass Deleted / Cancelled'),
        ('GATE_ADDED', 'New Security Gate Created'),
        ('GATE_EDITED', 'Security Gate Modified'),
        ('GATE_DELETED', 'Security Gate Deactivated / Deleted'),
        ('PROPERTY_CREATED', 'New Property Added'),
        ('PROPERTY_EDITED', 'Property Details Updated'),
        ('PROPERTY_DEACTIVATED', 'Property Deactivated'),
        ('USER_CREATED', 'Security User Created'),
        ('USER_EDITED', 'Security User Updated'),
        ('CLIENT_ONBOARDED', 'New Client Property Onboarded'),
        ('FEE_COLLECTED', 'Monthly Subscription Fee Collected'),
        ('SUBSCRIPTION_SUSPENDED', 'Client Property Suspended'),
        ('SUBSCRIPTION_REACTIVATED', 'Client Property Reactivated'),
        ('INVOICE_GENERATED', 'Monthly Invoice Generated'),
    ]
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    property = models.ForeignKey(Property, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
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


class PropertySubscriptionInvoice(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid / تم التحصيل'),
        ('unpaid', 'Unpaid / معلق'),
        ('overdue', 'Overdue / متأخر'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer / تحويل بنكي'),
        ('mada', 'Mada / مدى'),
        ('credit_card', 'Credit Card / بطاقة ائتمان'),
        ('cheque', 'Cheque / شيك مصدّق'),
        ('cash', 'Cash / نقداً'),
    ]
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=50, unique=True, help_text="e.g. INV-202609-RUH01")
    billing_period = models.CharField(max_length=50, help_text="e.g. September 2026")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1500.00)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unpaid')
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHOD_CHOICES, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Bank Ref / Receipt Number")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.invoice_number} - {self.property.code} ({self.amount} SAR - {self.status})"
