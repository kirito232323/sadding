from django.contrib import admin
from .models import Users, Employee, Rice, CustomerOrder, Supplier, Announcement, AuditLog, UserName, UserAddress, UserLog, Stock

admin.site.register(Users)
admin.site.register(Employee)
admin.site.register(Rice)
admin.site.register(CustomerOrder)
admin.site.register(Supplier)
admin.site.register(Announcement)
admin.site.register(AuditLog)

# Register additional models
admin.site.register(UserName)
admin.site.register(UserAddress)
admin.site.register(UserLog)
admin.site.register(Stock)

# Register your models here.
