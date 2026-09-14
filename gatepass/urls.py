from django.urls import path
from . import views

urlpatterns = [
    path('', views.gatepass_list, name='gatepass_list'),
    path('new/', views.gatepass_create, name='gatepass_create'),
    path('<int:pk>/', views.gatepass_detail, name='gatepass_detail'),
    path('<int:pk>/edit/', views.gatepass_edit, name='gatepass_edit'),
    path('<int:pk>/delete/', views.gatepass_delete, name='gatepass_delete'),
    path('<int:pk>/return/', views.gatepass_return, name='gatepass_return'),
    path('<int:pk>/print/', views.gatepass_print, name='gatepass_print'),
]
