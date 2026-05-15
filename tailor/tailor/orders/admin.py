from django.contrib import admin
from .models import Order, Payment, StyleGallery


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ['payment_date']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'amount', 'balance', 'status', 'delivery_date', 'created_at']
    list_filter = ['status', 'delivery_date', 'created_at']
    search_fields = ['customer__name', 'customer__phone', 'style_note']
    inlines = [PaymentInline]
    date_hierarchy = 'delivery_date'
    list_editable = ['status']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['order', 'amount', 'payment_method', 'payment_date']
    list_filter = ['payment_method', 'payment_date']
    search_fields = ['order__customer__name']


@admin.register(StyleGallery)
class StyleGalleryAdmin(admin.ModelAdmin):
    list_display = ['title', 'style_category', 'is_featured', 'created_at']
    list_filter = ['style_category', 'is_featured']
    search_fields = ['title', 'description']
