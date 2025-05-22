from webapp.models import Supplier, Employee, Users
from django.db import transaction

def fix_supplier_employees():
    updated = 0
    for supplier in Supplier.objects.all():
        # Only fix if employee is not set or is a Users instance
        user = supplier.employee
        if user and isinstance(user, Users):
            # Try to find Employee by username or name fields
            emp = Employee.objects.filter(Username=user.Username).first()
            if not emp:
                # Try by name fields if Username doesn't match
                emp = Employee.objects.filter(
                    FirstName=getattr(user.name, 'first_name', ''),
                    LastName=getattr(user.name, 'last_name', '')
                ).first()
            if emp:
                supplier.employee = emp
                supplier.save()
                updated += 1
    print(f"Updated {updated} supplier records to use Employee.")

if __name__ == "__main__":
    fix_supplier_employees()
