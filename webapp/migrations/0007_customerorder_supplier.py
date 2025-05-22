
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("webapp", "0006_supplier_employee_to_employee"),
    ]

    operations = [
        migrations.AddField(
            model_name="customerorder",
            name="supplier",
            field=models.ForeignKey(
                to="webapp.Supplier",
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                related_name="orders",
            ),
        ),
    ]
