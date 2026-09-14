from django.urls import path
from . import views

urlpatterns = [
    path('', views.visitor_list, name='visitor_list'),
    path('check-in/', views.visitor_checkin, name='visitor_checkin'),
    path('<int:pk>/', views.visitor_detail, name='visitor_detail'),
    path('<int:pk>/checkout/', views.visitor_checkout, name='visitor_checkout'),
    path('<int:pk>/pass/', views.visitor_pass_print, name='visitor_pass_print'),
]
