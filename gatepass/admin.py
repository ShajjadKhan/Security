from django.contrib import admin
from .models import GatePass, GatePassItem

class GatePassItemInline(admin.TabularInline):
    model = GatePassItem
    extra = 1

@admin.register(GatePass)
class GatePassAdmin(admin.ModelAdmin):
    list_display = ['pass_number', 'card_type', 'from_department', 'destination_entity', 'carrier_name', 'dispatched_at', 'expected_return_date', 'status']
    list_filter = ['card_type', 'status', 'from_department', 'purpose']
    search_fields = ['pass_number', 'physical_card_ref', 'destination_entity', 'carrier_name', 'carrier_phone', 'vehicle_plate']
    inlines = [GatePassItemInline]
