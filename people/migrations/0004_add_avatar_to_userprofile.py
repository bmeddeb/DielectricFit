from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0003_github_style_invitations'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='avatar',
            field=models.FileField(upload_to='avatars/', null=True, blank=True),
        ),
    ]

