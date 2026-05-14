from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/create/', views.customer_create, name='customer_create'),
    path('customers/search/', views.quick_search, name='quick_search'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    path('customers/<int:pk>/measurements/add/', views.add_measurement, name='add_measurement'),
    path('measurements/<int:pk>/delete/', views.delete_measurement, name='delete_measurement'),
    path('api/measurement-template/', views.get_measurement_template, name='measurement_template'),
    path('customers/<int:pk>/orders-partial/', views.customer_orders_partial, name='customer_orders_partial'),
]
