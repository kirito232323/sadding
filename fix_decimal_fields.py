from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from webapp.models import CustomerOrder  # Adjust accordingly

class Command(BaseCommand):
    help = 'Fix invalid decimal fields in CustomerOrder'

    def handle(self, *args, **options):
        count_fixed = 0
        orders = CustomerOrder.objects.all()
        for order in orders:
            fixed = False
            for field in ['cost_per_sack', 'total_cost', 'amount_paid', 'amount_change']:
                value = getattr(order, field)
                try:
                    Decimal(value)
                except (InvalidOperation, TypeError):
                    setattr(order, field, Decimal('0.00'))
                    fixed = True
            if fixed:
                order.save()
                count_fixed += 1
        self.stdout.write(self.style.SUCCESS(f'Fixed {count_fixed} orders'))
