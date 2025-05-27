from django.db import models
from django.shortcuts import get_object_or_404
from django.apps import apps
from datetime import datetime
from django.utils import timezone
from decimal import Decimal


class UserName(models.Model):
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=20, blank=True, null=True)
    last_name = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.first_name} {self.middle_name or ''} {self.last_name} {self.suffix or ''}".strip()

    class Meta:
        db_table = 'user_name'

class UserAddress(models.Model):
    house_unit_number = models.CharField(max_length=50, blank=True, null=True)
    building_name = models.CharField(max_length=100, blank=True, null=True)
    street_name = models.CharField(max_length=100, blank=True, null=True)
    barangay = models.CharField(max_length=100, blank=True, null=True)
    city_municipality = models.CharField(max_length=100, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.house_unit_number or ''} {self.building_name or ''} {self.street_name or ''}, {self.barangay or ''}, {self.city_municipality or ''}, {self.province or ''} {self.zip_code or ''}".strip()

    class Meta:
        db_table = 'user_address'

class Users(models.Model):
    UserID = models.AutoField(primary_key=True)
    name = models.OneToOneField(UserName, on_delete=models.CASCADE, related_name='user', null=True, blank=True)
    address = models.OneToOneField(UserAddress, on_delete=models.CASCADE, related_name='user', null=True, blank=True)
    Customer_Mobile_Number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        db_table = 'webapp_users'
        managed = True

from django.db import models

class Rice(models.Model):
    riceID = models.AutoField(primary_key=True)
    rice_type = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'Rice'

    def __str__(self):
        return f"{self.rice_type} ({self.packaging})"

from django.db import models
from .models import Rice 

class Stock(models.Model):
    stockID = models.AutoField(primary_key=True)
    rice_type = models.ForeignKey(Rice, on_delete=models.CASCADE, db_column='riceID', related_name='stocks')
    packaging = models.CharField(max_length=50, default='50kg')  # e.g., 25kg, 50kg
    price_per_sack = models.DecimalField(max_digits=10, decimal_places=2)
    stock_in = models.PositiveIntegerField(default=0)
    stock_out = models.PositiveIntegerField(default=0)
    current_stock = models.PositiveIntegerField(default=0)
    minimum_stock = models.PositiveIntegerField(default=10)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Stock'
        unique_together = ('rice_type', 'packaging')

    def __str__(self):
        return f"{self.rice_type.rice_type} - {self.packaging}"

    @property
    def rice_name(self):
        return self.rice_type.rice_type

    @property
    def description(self):
        return self.rice_type.description

    def save(self, *args, **kwargs):
        # Automatically compute current stock
        self.current_stock = self.stock_in - self.stock_out
        super().save(*args, **kwargs)



class CustomerOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ]
    DELIVERY_CHOICES = [
        ('delivery', 'Delivery'),
        ('pickup', 'Pickup')
    ]
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('gcash', 'GCash'),
        ('credit_card', 'Credit Card')
    ]

    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey('Users', on_delete=models.PROTECT)
    rice_type = models.ForeignKey('Rice', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    cost_per_sack = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_change = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    approval_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_type = models.CharField(max_length=20, choices=DELIVERY_CHOICES)
    delivery_status = models.CharField(max_length=20, default='pending')
    receiver_name = models.CharField(max_length=100)
    receiver_mobile_number = models.CharField(max_length=20)
    delivery_address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    handled_by = models.ForeignKey(
        'Employee',
        null=True,
        on_delete=models.SET_NULL,
        related_name='orders_handled'
    )
    employee = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders'
    )


    # New: Link to Supplier (nullable, optional)
    supplier = models.ForeignKey('Supplier', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    order_notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def customer_name(self):
        # Use the related UserName object for name fields
        if self.customer and self.customer.name:
            n = self.customer.name
            return f"{n.first_name} {n.middle_name or ''} {n.last_name} {n.suffix or ''}".strip()
        return str(self.customer) if self.customer else "Unknown"

    def __str__(self):
        if self.customer and self.customer.name:
            n = self.customer.name
            return f"Order #{self.order_id} by {n.first_name} {n.last_name} ({self.created_at.date()})"
        return f"Order #{self.order_id} by Unknown ({self.created_at.date()})"

    class Meta:
        db_table = 'webapp_customerorder'
        indexes = [
            models.Index(fields=['customer', 'created_at']),
        ]


class Supplier(models.Model):
    supplier_id = models.AutoField(primary_key=True)
    supplier_name = models.CharField(max_length=255)
    supplier_contact = models.CharField(max_length=50)
    rice_per_kilo = models.DecimalField(max_digits=10, decimal_places=2)
    kilo_of_rice = models.IntegerField()
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_method = models.CharField(max_length=50, default='Delivery')
    payment_method = models.CharField(max_length=50)
    employee = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, db_column='employee_id')
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, editable=False, blank=True, null=True)
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, blank=True, null=True)
    approval_status = models.CharField(max_length=20, default='Pending')
    purchase_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.rice_per_kilo and self.kilo_of_rice:
            self.total_cost = Decimal(self.rice_per_kilo) * Decimal(self.kilo_of_rice)
        if self.paid_amount is not None and self.total_cost is not None:
            self.change_amount = Decimal(self.paid_amount) - Decimal(self.total_cost)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.supplier_name} ({self.supplier_contact}) - {self.purchase_date.date()}"

    class Meta:
        db_table = 'webapp_supplier'
        verbose_name = "webapp_supplier"
        verbose_name_plural = "webapp_supplier"


class Employee(models.Model):
    EmployeeID = models.AutoField(primary_key=True)
    FirstName = models.CharField(max_length=50)
    MiddleName = models.CharField(max_length=50, blank=True, null=True)
    LastName = models.CharField(max_length=50)
    Suffix = models.CharField(max_length=20, blank=True, null=True)
    Role = models.CharField(max_length=100)
    Username = models.CharField(max_length=50, unique=True)
    Password = models.CharField(max_length=50)
    Account_Status = models.CharField(max_length=20, default='inactive')

    def __str__(self):
        return f"{self.FirstName} {self.LastName} ({self.Role})"

    class Meta:
        db_table = 'employee'


class Announcement(models.Model):
    announcement_id = models.AutoField(primary_key=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Announcement #{self.announcement_id} by {self.created_by}"

    class Meta:
        db_table = 'announcements'


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete')
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        'Users',
        on_delete=models.SET_NULL,
        null=True,
        to_field='UserID',
        db_column='user_id'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField()
    old_values = models.JSONField(null=True)
    new_values = models.JSONField(null=True)
    ip_address = models.GenericIPAddressField(null=True)

    class Meta:
        db_table = 'audit_log'
        ordering = ['-timestamp']


    def __str__(self):
        return f"{self.action} on {self.table_name} #{self.record_id} by {self.user}"

# --- UserLog model for user_logs table ---
class UserLog(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, db_column='employee_id')
    action_type = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_logs'