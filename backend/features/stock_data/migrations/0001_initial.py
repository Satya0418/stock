from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='StockPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(max_length=32)),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('open', models.DecimalField(decimal_places=4, max_digits=14)),
                ('high', models.DecimalField(decimal_places=4, max_digits=14)),
                ('low', models.DecimalField(decimal_places=4, max_digits=14)),
                ('close', models.DecimalField(decimal_places=4, max_digits=14)),
                ('volume', models.BigIntegerField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'db_table': 'stock_prices',
            },
        ),
        migrations.AddIndex(
            model_name='stockprice',
            index=models.Index(fields=['symbol', 'timestamp'], name='stock_prices_symbol_timestamp_idx'),
        ),
        migrations.AddConstraint(
            model_name='stockprice',
            constraint=models.UniqueConstraint(fields=['symbol', 'timestamp'], name='unique_symbol_timestamp'),
        ),
    ]
