import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Property, SecurityGate, User, SecurityAuditLog
from visitors.models import Visitor, DepartmentHost
from gatepass.models import GatePass
from lostfound.models import LostFoundItem

print('Seeding Multi-Property Architecture...')

# 1. Create Properties
prop1, created1 = Property.objects.get_or_create(
    code='PROP-RUH-01',
    defaults={
        'name': 'Riyadh Grand Palace Hotel',
        'name_ar': 'فندق قصر الرياض الكبير',
        'property_type': 'hotel',
        'city': 'Riyadh',
        'address': 'King Fahd Road, Al Olaya District',
        'contact_email': 'security.ruh@grandpalace.sa',
        'contact_phone': '+966 11 456 7890',
        'manager_name': 'Col. Fahad Al-Otaibi',
        'is_active': True,
    }
)
print(f'Property 1: {prop1} (Created: {created1})')

prop2, created2 = Property.objects.get_or_create(
    code='PROP-JED-02',
    defaults={
        'name': 'Jeddah Resort & Marina',
        'name_ar': 'منتجع ومارينا جدة الفاخر',
        'property_type': 'hotel',
        'city': 'Jeddah',
        'address': 'Corniche Road, North Obhur',
        'contact_email': 'security.jed@grandpalace.sa',
        'contact_phone': '+966 12 654 3210',
        'manager_name': 'Capt. Tariq Al-Ghamdi',
        'is_active': True,
    }
)
print(f'Property 2: {prop2} (Created: {created2})')

prop3, created3 = Property.objects.get_or_create(
    code='PROP-DMM-03',
    defaults={
        'name': 'Dammam Logistics Park & Hub',
        'name_ar': 'مجمع الدمام اللوجستي والمستودعات المركزية',
        'property_type': 'logistics',
        'city': 'Dammam',
        'address': 'Second Industrial City, Highway 615',
        'contact_email': 'logistics.sec@grandpalace.sa',
        'contact_phone': '+966 13 888 4422',
        'manager_name': 'Eng. Salem Al-Qahtani',
        'is_active': True,
    }
)
print(f'Property 3: {prop3} (Created: {created3})')

# 2. Link existing unassigned gates to Property 1 (Riyadh)
unassigned_gates = SecurityGate.objects.filter(property__isnull=True)
count_unassigned = unassigned_gates.count()
if count_unassigned > 0:
    unassigned_gates.update(property=prop1)
    print(f'Linked {count_unassigned} existing gates to {prop1.code}')

# 3. Create initial gates for Jeddah & Dammam if not exist
gates_data = [
    # Jeddah Gates
    (prop2, 'JED-GATE01', 'Main Corniche Gate & Barrier', 'بوابة الكورنيش الرئيسية والحاجز الأمني', 'main', 'Primary security gate for guest vehicles and taxis.'),
    (prop2, 'JED-GATE02', 'Marina & Yacht Club Access', 'بوابة المارينا ونادي اليخوت', 'vip', 'Security station for private yachts, boats, and VIP members.'),
    (prop2, 'JED-GATE03', 'Service & Catering Dock', 'رصيف الإمداد وخدمات الضيافة', 'service', 'Loading bay for F&B trucks and contractor equipment.'),
    
    # Dammam Logistics Gates
    (prop3, 'DMM-GATE01', 'Inbound Heavy Cargo Gate', 'بوابة دخول الشاحنات الثقيلة والحاويات', 'service', 'Weighbridge barrier and customs document inspection.'),
    (prop3, 'DMM-GATE02', 'Outbound Material Dispatch Ramp', 'منصة تفتيش وخروج البضائع المنقولة', 'service', 'Material pass verification and exit seal audit.'),
    (prop3, 'DMM-GATE03', 'Administrative Staff Gate', 'مدخل الموظفين والمفتشين المعتمدين', 'staff', 'Personnel badge scanner and biometric entrance.'),
]

for p, gcode, gname, gname_ar, gtype, gdesc in gates_data:
    gate_obj, g_created = SecurityGate.objects.get_or_create(
        code=gcode,
        defaults={
            'property': p,
            'name': gname,
            'name_ar': gname_ar,
            'gate_type': gtype,
            'description': gdesc,
            'is_active': True,
        }
    )
    if g_created:
        print(f'Created Gate {gate_obj.code} for {p.code}')

# 4. Link existing Users, Visitors, Passes, and Items to Property 1
User.objects.filter(assigned_property__isnull=True).update(assigned_property=prop1)
DepartmentHost.objects.filter(property__isnull=True).update(property=prop1)
Visitor.objects.filter(property__isnull=True).update(property=prop1)
GatePass.objects.filter(property__isnull=True).update(property=prop1)
LostFoundItem.objects.filter(property__isnull=True).update(property=prop1)
SecurityAuditLog.objects.filter(property__isnull=True).update(property=prop1)

# 5. Create Officers for Jeddah and Dammam if they don't exist
officers = [
    ('guard_jed1', 'Sultan', 'Al-Harbi', 'supervisor', 'SEC-JED-01', 'morning', prop2, 'JED-GATE01'),
    ('guard_jed2', 'Yasser', 'Al-Ghamdi', 'officer', 'SEC-JED-02', 'afternoon', prop2, 'JED-GATE02'),
    ('guard_dmm1', 'Mansour', 'Al-Dossary', 'supervisor', 'SEC-DMM-01', 'morning', prop3, 'DMM-GATE01'),
    ('guard_dmm2', 'Faisal', 'Al-Khaldi', 'officer', 'SEC-DMM-02', 'night', prop3, 'DMM-GATE02'),
]

for uname, fname, lname, role, badge, shift, prop, gate_code in officers:
    if not User.objects.filter(username=uname).exists():
        g = SecurityGate.objects.filter(code=gate_code).first()
        u = User.objects.create_user(
            username=uname,
            password='Password123!',
            first_name=fname,
            last_name=lname,
            role=role,
            badge_number=badge,
            shift=shift,
            assigned_property=prop,
            assigned_gate=g,
            is_on_duty=True
        )
        print(f'Provisioned officer: {u.username} ({badge}) at {prop.code}')

# 6. Create initial Audit log for multi-property deployment
secadmin = User.objects.filter(is_superuser=True).first()
if secadmin:
    SecurityAuditLog.objects.create(
        user=secadmin,
        property=prop1,
        action='PROPERTY_CREATED',
        reference='SYSTEM_MULTI_PROP_INIT',
        details='Corporate Multi-Property Master Architecture initialized across Riyadh, Jeddah, and Dammam properties.',
    )

print('Multi-Property Seeding Complete!')
