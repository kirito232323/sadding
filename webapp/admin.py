from django.contrib import admin
from .models import Users, Employee, Rice, CustomerOrder, Supplier, Announcement, AuditLog, UserName, UserAddress, UserLog, Stock, CustomerLedger

class CustomerOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 'customer', 'rice_type', 'quantity', 'payment_method',
        'approval_status', 'delivery_status', 'is_active', 'delivery_type', 'created_at', 'updated_at'
    )
    list_filter = ('approval_status', 'delivery_status', 'is_active', 'payment_method', 'delivery_type')
    search_fields = ('order_id', 'customer__name__first_name', 'customer__name__last_name')

admin.site.register(Users)
admin.site.register(Employee)
admin.site.register(Rice)
admin.site.register(CustomerOrder, CustomerOrderAdmin)
admin.site.register(Supplier)
admin.site.register(Announcement)
admin.site.register(AuditLog)

# Register additional models
admin.site.register(UserName)
admin.site.register(UserAddress)
admin.site.register(UserLog)
admin.site.register(Stock)
admin.site.register(CustomerLedger)

# Register your models here.
