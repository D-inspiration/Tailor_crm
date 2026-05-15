from django.contrib import admin
from .models import Customer, Measurement, MeasurementTemplate


class MeasurementInline(admin.TabularInline):
    model = Measurement
    extra = 1


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'gender', 'total_orders', 'created_at']
    list_filter = ['gender', 'created_at']
    search_fields = ['name', 'phone', 'address']
    inlines = [MeasurementInline]
    date_hierarchy = 'created_at'


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ['customer', 'measurement_name', 'value', 'created_at']
    list_filter = ['measurement_name', 'created_at']
    search_fields = ['customer__name', 'measurement_name']


@admin.register(MeasurementTemplate)
class MeasurementTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'gender', 'created_at']
    list_filter = ['gender']
