from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    path('search/', views.universal_search_view, name='universal_search'),
    path('gates/', views.gates_list_view, name='gates_list'),
    path('gates/<int:gate_id>/switch/', views.switch_duty_gate_view, name='switch_duty_gate'),
    path('set-lang/', views.set_language_view, name='set_language'),
]
