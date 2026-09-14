import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import SecurityGate, User
from gatepass.models import GatePass
from visitors.models import Visitor

gates_data = [
    {
        'code': 'GATE-01',
        'name': 'Gate 1 - Loading Dock & Service Ramp',
        'name_ar': 'بوابة 1 - رصيف الشحن والتحميل والخدمات',
        'gate_type': 'service',
        'description': 'Main cargo, logistics, contractors, and heavy supply entrance.'
    },
    {
        'code': 'GATE-02',
        'name': 'Gate 2 - Main Vehicle Barrier & Reception',
        'name_ar': 'بوابة 2 - المدخل الرئيسي والحاجز الأمني',
        'gate_type': 'main',
        'description': 'Hotel main entrance for guest vehicles and official visitors.'
    },
    {
        'code': 'GATE-03',
        'name': 'Gate 3 - Staff & Subcontractor West Gate',
        'name_ar': 'بوابة 3 - مدخل الموظفين والمقاولين الغربي',
        'gate_type': 'staff',
        'description': 'Biometric badge turnstile for staff and daily contractors.'
    },
    {
        'code': 'GATE-04',
        'name': 'Gate 4 - Basement Service Ramp & Parking',
        'name_ar': 'بوابة 4 - رامب قبو الخدمات ومواقف السيارات',
        'gate_type': 'basement',
        'description': 'Basement delivery bay and technical engineering access ramp.'
    },
]

for g_info in gates_data:
    gate, created = SecurityGate.objects.get_or_create(
        code=g_info['code'],
        defaults={
            'name': g_info['name'],
            'name_ar': g_info['name_ar'],
            'gate_type': g_info['gate_type'],
            'description': g_info['description'],
            'is_active': True,
        }
    )
    status = "Created" if created else "Existing"
    print(f"{status} Gate: {gate.code} - {gate.name}")

gate1 = SecurityGate.objects.filter(code='GATE-01').first()
gate2 = SecurityGate.objects.filter(code='GATE-02').first()

# Assign guard1 to Gate 1
guard1 = User.objects.filter(username='guard1').first()
if guard1 and gate1:
    guard1.assigned_gate = gate1
    guard1.save(update_fields=['assigned_gate'])

# Assign secadmin to Gate 1
secadmin = User.objects.filter(username='secadmin').first()
if secadmin and gate1:
    secadmin.assigned_gate = gate1
    secadmin.save(update_fields=['assigned_gate'])

# Link existing passes to gates
for gp in GatePass.objects.all():
    if not gp.gate:
        gp.gate = gate1
        gp.save(update_fields=['gate'])

# Link existing visitors to gates
for vis in Visitor.objects.all():
    if not vis.gate:
        vis.gate = gate2 or gate1
        vis.save(update_fields=['gate'])

print(f"Total Security Gates: {SecurityGate.objects.count()}")
print("Successfully linked users, passes, and visitors to perimeter gates!")
