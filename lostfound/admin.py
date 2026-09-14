from django.contrib import admin
from .models import LostFoundItem, ItemPhoto

class ItemPhotoInline(admin.TabularInline):
    model = ItemPhoto
    extra = 1

@admin.register(LostFoundItem)
class LostFoundItemAdmin(admin.ModelAdmin):
    list_display = ['reference_number', 'title', 'category', 'value_tier', 'found_location', 'found_date', 'status', 'days_in_custody']
    list_filter = ['status', 'category', 'value_tier', 'found_date']
    search_fields = ['reference_number', 'title', 'description', 'brand', 'serial_number', 'finder_name', 'claimant_name']
    inlines = [ItemPhotoInline]
