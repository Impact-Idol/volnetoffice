# Generated migration for HIPAA Password Security tables

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0117_hipaa_compliance_tables'),
    ]

    operations = [
        # =================================================================
        # PASSWORD HISTORY
        # =================================================================
        migrations.CreateModel(
            name='PasswordHistory',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_history', to='db.user')),
                ('password_hash', models.CharField(help_text='Hashed password for comparison', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'verbose_name': 'Password History',
                'verbose_name_plural': 'Password Histories',
                'db_table': 'password_history',
                'ordering': ['-created_at'],
            },
        ),

        # =================================================================
        # FAILED LOGIN ATTEMPTS
        # =================================================================
        migrations.CreateModel(
            name='FailedLoginAttempt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='failed_logins', to='db.user')),
                ('identifier', models.CharField(db_index=True, help_text='Email or username attempted', max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, db_index=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('attempted_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('reason', models.CharField(
                    choices=[
                        ('invalid_password', 'Invalid Password'),
                        ('user_not_found', 'User Not Found'),
                        ('account_disabled', 'Account Disabled'),
                        ('account_locked', 'Account Locked'),
                        ('mfa_failed', 'MFA Failed'),
                    ],
                    default='invalid_password',
                    max_length=50
                )),
            ],
            options={
                'verbose_name': 'Failed Login Attempt',
                'verbose_name_plural': 'Failed Login Attempts',
                'db_table': 'failed_login_attempts',
                'ordering': ['-attempted_at'],
            },
        ),

        # =================================================================
        # ACCOUNT LOCKOUTS
        # =================================================================
        migrations.CreateModel(
            name='AccountLockout',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lockouts', to='db.user')),
                ('locked_at', models.DateTimeField(auto_now_add=True)),
                ('locked_until', models.DateTimeField(blank=True, help_text='When the lockout expires (null = manual unlock required)', null=True)),
                ('reason', models.CharField(
                    choices=[
                        ('failed_logins', 'Too Many Failed Login Attempts'),
                        ('admin_action', 'Administrative Action'),
                        ('security_incident', 'Security Incident'),
                        ('suspicious_activity', 'Suspicious Activity'),
                    ],
                    default='failed_logins',
                    max_length=50
                )),
                ('unlocked_at', models.DateTimeField(blank=True, null=True)),
                ('unlocked_by_id', models.UUIDField(blank=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={
                'verbose_name': 'Account Lockout',
                'verbose_name_plural': 'Account Lockouts',
                'db_table': 'account_lockouts',
                'ordering': ['-locked_at'],
            },
        ),

        # Add indexes
        migrations.AddIndex(
            model_name='failedloginattempt',
            index=models.Index(fields=['identifier', 'attempted_at'], name='failed_login_ident_time_idx'),
        ),
        migrations.AddIndex(
            model_name='failedloginattempt',
            index=models.Index(fields=['ip_address', 'attempted_at'], name='failed_login_ip_time_idx'),
        ),
    ]
