# Generated manually to allow blank/null values for Badge icon and description

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_remove_user_transaction_count_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='badge',
            name='icon',
            field=models.ImageField(blank=True, null=True, upload_to='badges/'),
        ),
        migrations.AlterField(
            model_name='badge',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
    ]
