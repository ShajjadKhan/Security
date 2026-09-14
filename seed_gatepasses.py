import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from core.models import User, SecurityAuditLog
from visitors.models import DepartmentHost
from gatepass.models import GatePass, GatePassItem

guard1 = User.objects.filter(username='guard1').first() or User.objects.first()
secadmin = User.objects.filter(username='secadmin').first() or User.objects.first()

eng_dept = DepartmentHost.objects.filter(name__icontains='Engineering').first()
it_dept = DepartmentHost.objects.filter(name__icontains='Information Technology').first() or DepartmentHost.objects.filter(name__icontains='Executive').first()
hk_dept = DepartmentHost.objects.filter(name__icontains='Housekeeping').first()
fb_dept = DepartmentHost.objects.filter(name__icontains='Food').first() or DepartmentHost.objects.first()

now = timezone.now()

# Clear existing passes
GatePass.objects.all().delete()

# 1. Active Green Card (Returnable - due in 5 days)
gp1 = GatePass.objects.create(
    card_type='GREEN',
    physical_card_ref='Card #07',
    from_department=eng_dept,
    sender_name='Ahmed Farooq (Senior MEP Tech)',
    sender_email='a.farooq@hotel.com',
    sender_phone='+966509871234',
    destination_entity='Al-Futtaim Technical Workshop',
    destination_address='Industrial Area 2, Street 18, Riyadh',
    destination_contact_name='Eng. Basel Mansoor',
    destination_phone='+966114889900',
    carrier_name='Mohammed Aslam',
    carrier_phone='+966501234567',
    carrier_id_number='2488192019',
    carrier_company='Al-Futtaim Logistics Fleet',
    vehicle_plate='4921 RKD',
    vehicle_model='White Isuzu Medium Cargo Truck',
    purpose='repair',
    purpose_notes='Primary chiller circulation pump motor winding inspection & bearing replacement.',
    authorized_by_manager='Eng. Tariq Al-Mansoor (Chief Engineer)',
    gate_location='Loading Dock Gate',
    dispatched_by=guard1,
    dispatched_at=now - timezone.timedelta(days=2),
    expected_return_date=now + timezone.timedelta(days=5),
    status='active',
    security_notes='Gate guard verified vehicle cargo against serial numbers. Gate pass copy issued to driver.'
)
GatePassItem.objects.create(
    pass_card=gp1,
    item_name='Chiller Water Circulation Pump 5.5HP',
    quantity=1,
    unit='pcs',
    serial_asset_tag='ASSET-ENG-PUMP-409',
    condition_out='for_repair'
)
GatePassItem.objects.create(
    pass_card=gp1,
    item_name='Electric 2-Way Actuator Valves 3-Inch',
    quantity=2,
    unit='pcs',
    serial_asset_tag='ASSET-ENG-ACT-12B',
    condition_out='for_repair'
)

# 2. Overdue Green Card (Returnable - due 3 days ago!)
gp2 = GatePass.objects.create(
    card_type='GREEN',
    physical_card_ref='Card #12',
    from_department=it_dept,
    sender_name='Sarah Al-Otaibi (AV Supervisor)',
    sender_email='av.dept@hotel.com',
    sender_phone='+966551239876',
    destination_entity='Al-Khozama Exhibition Center, Hall B',
    destination_address='King Fahd Road, Riyadh',
    destination_contact_name='Fahad Al-Husseini (Event Director)',
    destination_phone='+966558877112',
    carrier_name='Kareem Ziyad',
    carrier_phone='+966559876543',
    carrier_id_number='2311495022',
    carrier_company='In-House Transport Service',
    vehicle_plate='1823 KSA',
    vehicle_model='White Toyota Hilux Pickup',
    purpose='demo',
    purpose_notes='High-brightness laser projectors loaned for GCC Hospitality Tech Summit.',
    authorized_by_manager='Rashid Al-Zahrani (Director of IT)',
    gate_location='Loading Dock Gate',
    dispatched_by=guard1,
    dispatched_at=now - timezone.timedelta(days=10),
    expected_return_date=now - timezone.timedelta(days=3),  # OVERDUE!
    status='active',
    security_notes='Urgent reminder: exhibition concluded 3 days ago. Items still in field.'
)
GatePassItem.objects.create(
    pass_card=gp2,
    item_name='Sony 4K High-Lumen Laser Projector',
    quantity=2,
    unit='pcs',
    serial_asset_tag='IT-PROJ-8801 & 8802',
    condition_out='good'
)
GatePassItem.objects.create(
    pass_card=gp2,
    item_name='Shure Wireless Microphone Kit (Dual Channel)',
    quantity=4,
    unit='sets',
    serial_asset_tag='IT-MIC-04-KIT',
    condition_out='good'
)

# 3. Partially Returned Green Card
gp3 = GatePass.objects.create(
    card_type='GREEN',
    physical_card_ref='Card #03',
    from_department=hk_dept or eng_dept,
    sender_name='Nadia Salim (Laundry Assistant Mgr)',
    sender_email='laundry@hotel.com',
    sender_phone='+966541122334',
    destination_entity='CleanCo Commercial Laundry Equipment Service',
    destination_address='Al-Sulay Industrial District, Riyadh',
    destination_contact_name='Ramesh Nair',
    destination_phone='+966112998811',
    carrier_name='Bilal Naser',
    carrier_phone='+966543219876',
    carrier_id_number='2109845511',
    carrier_company='CleanCo Service Van',
    vehicle_plate='7744 TXD',
    vehicle_model='Hyundai H1 Cargo Van',
    purpose='repair',
    purpose_notes='Commercial high-pressure boiler iron servicing and thermostatic recalibration.',
    authorized_by_manager='Elena Rostova (Executive Housekeeper)',
    gate_location='Loading Dock Gate',
    dispatched_by=guard1,
    dispatched_at=now - timezone.timedelta(days=6),
    expected_return_date=now + timezone.timedelta(days=1),
    actual_return_date=now - timezone.timedelta(hours=4),
    received_by=secadmin,
    status='partially_returned',
    security_notes='[Partial Return]: 2 iron units returned repaired and operational. 2 remaining at workshop awaiting heating element parts.'
)
item3_1 = GatePassItem.objects.create(
    pass_card=gp3,
    item_name='Industrial High-Pressure Steam Iron Station',
    quantity=4,
    unit='pcs',
    serial_asset_tag='HK-IRON-01 to 04',
    condition_out='for_repair',
    quantity_returned=2,
    condition_returned='repaired',
    is_returned=False
)

# 4. Red Card #1: Scrap Metal Disposal (Permanent Out)
gp4 = GatePass.objects.create(
    card_type='RED',
    physical_card_ref='RED-DISP-088',
    from_department=fb_dept,
    sender_name='Chef Marco De Luca (Exec Chef)',
    sender_email='kitchen.admin@hotel.com',
    sender_phone='+966503344556',
    destination_entity='Riyadh Metal Recycling & Scrap Yard Co.',
    destination_address='Southern Ring Road, Exit 21, Riyadh',
    destination_contact_name='Sami Al-Mutawa',
    destination_phone='+966554400119',
    carrier_name='Farhan Ali',
    carrier_phone='+966567890123',
    carrier_id_number='2501982736',
    carrier_company='Al-Jazirah Scrap Recovery Fleet',
    vehicle_plate='3301 BDL',
    vehicle_model='Mercedes Heavy Scrap Truck',
    purpose='scrap',
    purpose_notes='Condemned banquet chairs and decommissioned damaged stainless steel preparation tables from kitchen renovation.',
    authorized_by_manager='Khaled Al-Ghamdi (Director of Finance)',
    gate_location='Loading Dock Gate',
    dispatched_by=secadmin,
    dispatched_at=now - timezone.timedelta(hours=5),
    status='dispatched_closed',
    security_notes='Finance scrap disposal invoice SCR-2026-91 verified. Guard inspected truck bed empty prior to loading.'
)
GatePassItem.objects.create(
    pass_card=gp4,
    item_name='Damaged Banquet Steel Chairs (Bent Frames/Torn Upholstery)',
    quantity=45,
    unit='pcs',
    serial_asset_tag='SCRAP-CHAIR-BATCH-2026',
    condition_out='damaged'
)
GatePassItem.objects.create(
    pass_card=gp4,
    item_name='Decommissioned Stainless Steel Kitchen Prep Tables',
    quantity=6,
    unit='pcs',
    serial_asset_tag='SCRAP-TABLE-01-06',
    condition_out='damaged'
)

# 5. Red Card #2: Guest Left-Behind Courier (Permanent Out)
gp5 = GatePass.objects.create(
    card_type='RED',
    physical_card_ref='RED-GUEST-014',
    from_department=DepartmentHost.objects.filter(name__icontains='Front').first() or fb_dept,
    sender_name='Layla Al-Amri (Duty Manager)',
    sender_email='concierge@hotel.com',
    sender_phone='+966500011223',
    destination_entity='DHL Express International Courier Central',
    destination_address='Airport Cargo Village, Terminal 1 Road, Riyadh',
    destination_contact_name='DHL Dispatch Counter',
    destination_phone='+966114008800',
    carrier_name='Rami Al-Khatib',
    carrier_phone='+966504433221',
    carrier_id_number='2201994821',
    carrier_company='DHL Express KSA',
    vehicle_plate='5512 DHL',
    vehicle_model='Yellow DHL Cargo Van',
    purpose='guest_property',
    purpose_notes='Guest left briefcase and laptop in Room 814 after checkout. Dispatching via express air courier to guest address in Dubai, UAE.',
    authorized_by_manager='Mansoor Al-Husseini (Hotel Resident Manager)',
    gate_location='Main Gate Alpha',
    dispatched_by=guard1,
    dispatched_at=now - timezone.timedelta(hours=2),
    status='dispatched_closed',
    security_notes='Airway Bill DHL-9921448102 verified and attached. Guest credit card pre-authorized for shipping fees.'
)
GatePassItem.objects.create(
    pass_card=gp5,
    item_name='Sealed Diplomatic Pouch (Laptop, Suitcase, Guest Documents)',
    quantity=1,
    unit='boxes',
    serial_asset_tag='AWB-DHL-9921448102',
    condition_out='good'
)

# Add Audit Logs
SecurityAuditLog.objects.create(
    user=guard1,
    action='CHECK_OUT',
    reference=gp1.pass_number,
    details=f"Gate Dispatch: Green Card {gp1.pass_number} (Card #07) issued. Carrier: Mohammed Aslam (Plate: 4921 RKD). Destination: Al-Futtaim Workshop. Due: {gp1.expected_return_date.strftime('%d-%b %H:%M')}.",
    ip_address='127.0.0.1'
)
SecurityAuditLog.objects.create(
    user=guard1,
    action='CHECK_OUT',
    reference=gp2.pass_number,
    details=f"Gate Dispatch: Green Card {gp2.pass_number} (Card #12) issued. Projectors and mics for GCC Summit.",
    ip_address='127.0.0.1'
)
SecurityAuditLog.objects.create(
    user=secadmin,
    action='CHECK_IN',
    reference=gp3.pass_number,
    details=f"Inward Gate Handover: Partial return for {gp3.pass_number} (Card #03). 2 of 4 steam irons returned repaired by CleanCo.",
    ip_address='127.0.0.1'
)
SecurityAuditLog.objects.create(
    user=secadmin,
    action='SECURITY_ALERT',
    reference=gp4.pass_number,
    details=f"Gate Dispatch: Red Card {gp4.pass_number} permanent exit. 45 scrap banquet chairs & 6 steel tables dispatched to Riyadh Metal Recycling.",
    ip_address='127.0.0.1'
)
SecurityAuditLog.objects.create(
    user=guard1,
    action='CHECK_OUT',
    reference=gp5.pass_number,
    details=f"Gate Dispatch: Red Card {gp5.pass_number} guest property dispatched via DHL Courier (AWB DHL-9921448102).",
    ip_address='127.0.0.1'
)

print(f"Successfully seeded {GatePass.objects.count()} Gate Passes with manifest items and security audit logs!")
