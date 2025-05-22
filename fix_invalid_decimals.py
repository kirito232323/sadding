# Django shell script to fix invalid decimal fields in CustomerOrder
from decimal import Decimal, InvalidOperation
from webapp.models import CustomerOrder

fields = ['cost_per_sack', 'total_cost', 'amount_paid', 'amount_change']
fixed_count = 0

for order in CustomerOrder.objects.all():
    needs_save = False
    for field in fields:
        value = getattr(order, field)
        try:
            # If value is None or empty string, or not a valid decimal, fix it
            if value is None or (isinstance(value, str) and value.strip() == ''):
                print(f"Order {order.order_id}: {field} is empty. Setting to 0.00")
                setattr(order, field, Decimal('0.00'))
                needs_save = True
            else:
                # Try to cast to Decimal to catch invalid values
                Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            print(f"Order {order.order_id}: {field} is invalid ({value}). Setting to 0.00")
            setattr(order, field, Decimal('0.00'))
            needs_save = True
    if needs_save:
        order.save()
        fixed_count += 1

print(f"Done. Fixed {fixed_count} orders with invalid decimal fields.")
