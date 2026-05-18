from django.db import models
from django.urls import reverse


class Order(models.Model):
    flask_user_id = models.IntegerField(db_index=True)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    style_note = models.TextField(blank=True)
    style_image = models.ImageField(
        upload_to='style_images/%Y/%m/',
        blank=True,
        null=True
    )
    fabric_details = models.TextField(blank=True)
    delivery_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'delivery_date']),
            models.Index(fields=['customer', 'status']),
        ]

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'pk': self.pk})

    @property
    def is_paid(self):
        return self.balance <= 0

    @property
    def payment_status(self):
        if self.balance <= 0:
            return 'paid'
        elif self.amount > 0 and self.balance < self.amount:
            return 'partial'
        return 'unpaid'

    @property
    def days_until_delivery(self):
        from datetime import date
        if self.delivery_date:
            delta = (self.delivery_date - date.today()).days
            return delta
        return None


class Payment(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment_method = models.CharField(
        max_length=50,
        choices=[
            ('cash', 'Cash'),
            ('transfer', 'Bank Transfer'),
            ('pos', 'POS'),
            ('other', 'Other'),
        ],
        default='cash'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment ₦{self.amount} for Order #{self.order.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update order balance
        self.order.balance = self.order.amount - sum(
            p.amount for p in self.order.payments.all()
        )
        self.order.save(update_fields=['balance'])


class StyleGallery(models.Model):
    """Store finished work photos for portfolio/marketing."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        null=True,
        blank=True
    )
    image = models.ImageField(upload_to='gallery/%Y/%m/')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    style_category = models.CharField(
        max_length=50,
        choices=[
            ('senator', 'Senator'),
            ('agbada', 'Agbada'),
            ('suit', 'Suit'),
            ('gown', 'Gown'),
            ('native', 'Native Wear'),
            ('other', 'Other'),
        ],
        default='other'
    )
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Style Galleries'

    def __str__(self):
        return self.title or f"Gallery Image #{self.id}"
