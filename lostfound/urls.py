from django.urls import path
from . import views

urlpatterns = [
    path('', views.lostfound_list, name='lostfound_list'),
    path('new/', views.lostfound_create, name='lostfound_create'),
    path('<int:pk>/', views.lostfound_detail, name='lostfound_detail'),
    path('<int:pk>/claim/', views.lostfound_claim, name='lostfound_claim'),
]
