from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('audit-log/', views.audit_log_view, name='audit_log'),
    path('search/', views.universal_search_view, name='universal_search'),
]
