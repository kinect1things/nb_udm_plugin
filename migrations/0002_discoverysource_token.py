from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('nb_udm_plugin', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='discoverysource',
            name='token',
            field=models.CharField(
                blank=True,
                default='',
                help_text='API token for this source. Falls back to NB_UDM_UNIFI_TOKEN env var if blank.',
                max_length=255,
            ),
        ),
    ]
