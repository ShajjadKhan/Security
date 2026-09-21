from django.urls import path
from . import views
from . import views_admin

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('dashboard/', views.dashboard_view, name='dashboard_alias'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    path('search/', views.universal_search_view, name='universal_search'),
    path('gates/', views.gates_list_view, name='gates_list'),
    path('gates/<int:gate_id>/switch/', views.switch_duty_gate_view, name='switch_duty_gate'),
    path('gates/<int:gate_id>/edit/', views.gate_edit_view, name='gate_edit'),
    path('gates/<int:gate_id>/delete/', views.gate_delete_view, name='gate_delete'),
    path('set-lang/', views.set_language_view, name='set_language'),

    # Super Admin Master Hub & Property Regulation
    path('super-admin/', views_admin.super_admin_dashboard_view, name='super_admin_dashboard'),
    path('super-admin/properties/create/', views_admin.property_create_view, name='property_create'),
    path('super-admin/properties/<int:property_id>/edit/', views_admin.property_edit_view, name='property_edit'),
    path('super-admin/properties/<int:property_id>/toggle/', views_admin.property_toggle_view, name='property_toggle'),
    path('super-admin/properties/<int:property_id>/suspend/', views_admin.property_suspend_toggle_view, name='property_suspend_toggle'),
    path('super-admin/billing/collect/<int:property_id>/', views_admin.collect_fee_view, name='collect_fee'),
    path('super-admin/billing/generate-invoices/', views_admin.generate_monthly_invoices_view, name='generate_monthly_invoices'),
    path('properties/<str:property_id>/switch/', views_admin.property_switch_view, name='property_switch'),
    path('super-admin/users/create/', views_admin.user_create_view, name='user_create'),
    path('super-admin/users/<int:user_id>/edit/', views_admin.user_edit_view, name='user_edit'),
    path('subscription-suspended/', views.subscription_suspended_view, name='subscription_suspended'),
    path('sw.js', views.service_worker_view, name='service_worker'),
    path('manifest.json', views.manifest_view, name='manifest_json'),
]
