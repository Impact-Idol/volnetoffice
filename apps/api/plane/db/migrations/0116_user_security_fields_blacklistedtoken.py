# Generated manually for Sprint 3: Core Security

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0115_auto_20260105_1406'),
    ]

    operations = [
        # Add token_version field to User for session revocation
        migrations.AddField(
            model_name='user',
            name='token_version',
            field=models.IntegerField(
                default=0,
                help_text='Incremented when user sessions are revoked. Used to invalidate JWTs.',
            ),
        ),
        # Add sso_bypass field to User for break glass access
        migrations.AddField(
            model_name='user',
            name='sso_bypass',
            field=models.BooleanField(
                default=False,
                help_text='Allow this super admin to bypass SSO for emergency access.',
            ),
        ),
        # Create BlacklistedToken model for audit trail
        migrations.CreateModel(
            name='BlacklistedToken',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('token_version', models.IntegerField(help_text='The token version that was blacklisted')),
                ('reason', models.CharField(default='Session revocation', help_text='Reason for blacklisting', max_length=255)),
                ('initiated_by', models.CharField(blank=True, help_text='Email of admin who initiated the revocation', max_length=255, null=True)),
                ('revoked_at', models.DateTimeField(default=django.utils.timezone.now, help_text='When the tokens were revoked')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blacklisted_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Blacklisted Token',
                'verbose_name_plural': 'Blacklisted Tokens',
                'db_table': 'blacklisted_tokens',
                'ordering': ('-revoked_at',),
            },
        ),
        # Add index for efficient token validation lookups
        migrations.AddIndex(
            model_name='blacklistedtoken',
            index=models.Index(fields=['user', 'token_version'], name='blacklisted_user_id_token_v_idx'),
        ),
    ]
