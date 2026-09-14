from django.contrib import admin
from .models import Visitor, DepartmentHost

@admin.register(DepartmentHost)
class DepartmentHostAdmin(admin.ModelAdmin):
    list_display = ['name', 'floor_room', 'contact_person', 'contact_phone']

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['pass_number', 'full_name', 'category', 'phone', 'host_department', 'check_in_time', 'check_out_time', 'status']
    list_filter = ['status', 'category', 'gate_location', 'check_in_time']
    search_fields = ['pass_number', 'full_name', 'phone', 'id_number', 'vehicle_plate', 'company_name']
