from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from customers.views import login_with_flask
from payments import views as payment_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/login/', login_with_flask, name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('', include('customers.urls')),
    path('orders/', include('orders.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('upgrade/', payment_views.upgrade_plan, name='upgrade_plan'),
    path('checkout/<str:plan>/', payment_views.checkout, name='checkout'),
    path('payments/callback/', payment_views.payment_callback, name='payment_callback'),
    path('payments/webhook/', payment_views.monnify_webhook, name='monnify_webhook'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
