from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('webapp', '0005_alter_customerorder_amount_change_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='supplier',
            name='employee',
            field=models.ForeignKey(
                to='webapp.Employee',
                on_delete=django.db.models.deletion.SET_NULL,
                null=True,
                db_column='employee_id',
            ),
        ),
    ]
