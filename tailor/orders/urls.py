from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('create/', views.order_create, name='order_create'),
    path('search/', views.order_search, name='order_search'),
    path('<int:pk>/', views.order_detail, name='order_detail'),
    path('<int:pk>/edit/', views.order_edit, name='order_edit'),
    path('<int:pk>/delete/', views.order_delete, name='order_delete'),
    path('<int:pk>/status/', views.update_status, name='update_status'),
    path('<int:pk>/payments/add/', views.add_payment, name='add_payment'),
    path('payments/<int:pk>/delete/', views.delete_payment, name='delete_payment'),
    path('gallery/', views.gallery_list, name='gallery_list'),
    path('gallery/create/', views.gallery_create, name='gallery_create'),
]
