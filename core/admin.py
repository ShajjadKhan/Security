from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SecurityAuditLog

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Security Department Info', {'fields': ('role', 'badge_number', 'phone', 'shift', 'is_on_duty')}),
    )
    list_display = ['username', 'email', 'get_full_name', 'role', 'badge_number', 'shift', 'is_on_duty']
    list_filter = ['role', 'shift', 'is_on_duty']

admin.site.register(User, CustomUserAdmin)

@admin.register(SecurityAuditLog)
class SecurityAuditLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'action', 'reference', 'user', 'ip_address']
    list_filter = ['action', 'created_at']
    search_fields = ['reference', 'details']
