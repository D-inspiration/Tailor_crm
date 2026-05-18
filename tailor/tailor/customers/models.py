from django.db import models
from django.urls import reverse


class Customer(models.Model):
    flask_user_id = models.IntegerField(db_index=True) 
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, unique=True, db_index=True)
    address = models.TextField(blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['phone']),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    def get_absolute_url(self):
        return reverse('customer_detail', kwargs={'pk': self.pk})

    @property
    def total_orders(self):
        return self.orders.count()

    @property
    def total_revenue(self):
        return sum(order.amount for order in self.orders.all())

    @property
    def outstanding_balance(self):
        return sum(order.balance for order in self.orders.all() if order.balance > 0)

    @property
    def latest_measurement(self):
        return self.measurements.first()


class Measurement(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='measurements')
    measurement_name = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.measurement_name}: {self.value}"


class MeasurementTemplate(models.Model):
    name = models.CharField(max_length=100, unique=True)
    gender = models.CharField(max_length=10, choices=Customer.GENDER_CHOICES)
    fields = models.JSONField(default=list, help_text='List of measurement field names')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
