# Generated migration for HIPAA Compliance tables

import uuid
from django.db import migrations, models
import django.contrib.postgres.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0116_user_security_fields_blacklistedtoken'),
    ]

    operations = [
        # Enable pgcrypto extension for database-level encryption
        migrations.RunSQL(
            "CREATE EXTENSION IF NOT EXISTS pgcrypto;",
            reverse_sql="DROP EXTENSION IF EXISTS pgcrypto;"
        ),

        # =================================================================
        # AUDIT LOGS
        # =================================================================
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('action', models.CharField(db_index=True, help_text='The action performed', max_length=100)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, help_text='When the action occurred')),
                ('user_id', models.UUIDField(blank=True, db_index=True, help_text='UUID of the user who performed the action', null=True)),
                ('user_email_hash', models.CharField(blank=True, help_text='SHA-256 hash of user email', max_length=64, null=True)),
                ('actor_type', models.CharField(default='user', help_text='Type of actor: user, system, api_token, webhook', max_length=50)),
                ('workspace_id', models.UUIDField(blank=True, db_index=True, help_text='UUID of the workspace context', null=True)),
                ('workspace_slug', models.CharField(blank=True, help_text='Slug of the workspace', max_length=255, null=True)),
                ('project_id', models.UUIDField(blank=True, db_index=True, help_text='UUID of the project context', null=True)),
                ('resource_type', models.CharField(blank=True, db_index=True, help_text='Type of resource accessed', max_length=50, null=True)),
                ('resource_id', models.UUIDField(blank=True, db_index=True, help_text='UUID of the specific resource', null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, help_text='IP address of the request', null=True)),
                ('user_agent', models.TextField(blank=True, help_text='User agent string from the request', null=True)),
                ('request_id', models.CharField(blank=True, help_text='Unique request identifier for correlation', max_length=64, null=True)),
                ('session_id', models.CharField(blank=True, help_text='Session identifier', max_length=64, null=True)),
                ('data', models.JSONField(default=dict, help_text='Additional structured data about the action')),
                ('changes', models.JSONField(blank=True, default=dict, help_text='Before/after values for update operations', null=True)),
                ('phi_accessed', models.BooleanField(db_index=True, default=False, help_text='Whether PHI was accessed')),
                ('phi_fields', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), blank=True, default=list, help_text='List of PHI fields accessed', size=None)),
                ('checksum', models.CharField(help_text='SHA-256 checksum for integrity verification', max_length=64)),
                ('severity', models.CharField(choices=[('debug', 'Debug'), ('info', 'Info'), ('warning', 'Warning'), ('error', 'Error'), ('critical', 'Critical')], default='info', help_text='Severity level of the audit event', max_length=20)),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'db_table': 'audit_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'timestamp'], name='audit_logs_action_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user_id', 'timestamp'], name='audit_logs_user_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['resource_type', 'resource_id'], name='audit_logs_resource_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['phi_accessed', 'timestamp'], name='audit_logs_phi_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['workspace_id', 'project_id', 'timestamp'], name='audit_logs_ws_proj_time_idx'),
        ),

        # =================================================================
        # PHI ACCESS LOGS
        # =================================================================
        migrations.CreateModel(
            name='PHIAccessLog',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('audit_log', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='phi_access_logs', to='db.auditlog')),
                ('phi_category', models.CharField(choices=[('demographics', 'Demographics'), ('contact', 'Contact Information'), ('health', 'Health Information'), ('financial', 'Financial Information'), ('employment', 'Employment Information'), ('case_notes', 'Case Notes'), ('attachments', 'Attachments')], help_text='Category of PHI accessed', max_length=50)),
                ('access_reason', models.CharField(blank=True, help_text='Documented reason for accessing PHI', max_length=255, null=True)),
                ('data_subject_id', models.UUIDField(blank=True, db_index=True, help_text='UUID of the person whose PHI was accessed', null=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'verbose_name': 'PHI Access Log',
                'verbose_name_plural': 'PHI Access Logs',
                'db_table': 'phi_access_logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='phiaccesslog',
            index=models.Index(fields=['phi_category', 'timestamp'], name='phi_access_category_time_idx'),
        ),
        migrations.AddIndex(
            model_name='phiaccesslog',
            index=models.Index(fields=['data_subject_id', 'timestamp'], name='phi_access_subject_time_idx'),
        ),

        # =================================================================
        # RETENTION POLICIES
        # =================================================================
        migrations.CreateModel(
            name='RetentionPolicy',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Human-readable policy name', max_length=100, unique=True)),
                ('description', models.TextField(blank=True, help_text='Description of this retention policy')),
                ('retention_days', models.IntegerField(default=2555, help_text='Days from date of entry to retain. Max: 2555 (7 years).', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(2555)])),
                ('data_type', models.CharField(choices=[('attachment', 'File Attachments'), ('issue', 'Issues'), ('issue_comment', 'Issue Comments'), ('audit_log', 'Audit Logs'), ('user', 'User Data'), ('project', 'Projects'), ('page', 'Pages'), ('notification', 'Notifications'), ('session', 'Sessions'), ('api_log', 'API Activity Logs')], help_text='Type of data this policy applies to', max_length=50)),
                ('archive_before_delete', models.BooleanField(default=True, help_text='Archive data to cold storage before deletion')),
                ('only_archived', models.BooleanField(default=True, help_text='Only apply to already-archived/soft-deleted records')),
                ('require_approval', models.BooleanField(default=False, help_text='Require manual approval before deletion')),
                ('is_active', models.BooleanField(default=True, help_text='Whether this policy is actively enforced')),
                ('workspace_id', models.UUIDField(blank=True, db_index=True, help_text='Workspace this policy applies to (null = global)', null=True)),
            ],
            options={
                'verbose_name': 'Retention Policy',
                'verbose_name_plural': 'Retention Policies',
                'db_table': 'retention_policies',
                'ordering': ['data_type', 'name'],
            },
        ),
        migrations.AddConstraint(
            model_name='retentionpolicy',
            constraint=models.UniqueConstraint(fields=('data_type', 'workspace_id'), name='unique_policy_per_data_type_workspace'),
        ),

        # =================================================================
        # RETENTION EXEMPTIONS (Legal Holds)
        # =================================================================
        migrations.CreateModel(
            name='RetentionExemption',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('resource_type', models.CharField(choices=[('attachment', 'File Attachment'), ('issue', 'Issue'), ('project', 'Project'), ('workspace', 'Workspace'), ('user', 'User'), ('page', 'Page')], help_text='Type of resource under hold', max_length=50)),
                ('resource_id', models.UUIDField(db_index=True, help_text='UUID of the resource under hold')),
                ('reason', models.TextField(help_text='Reason for the legal hold')),
                ('legal_case_number', models.CharField(blank=True, help_text='Associated legal case number', max_length=100)),
                ('requesting_party', models.CharField(blank=True, help_text='Party who requested the hold', max_length=255)),
                ('hold_start', models.DateTimeField(auto_now_add=True, help_text='When the hold was placed')),
                ('hold_until', models.DateTimeField(blank=True, help_text='When the hold expires (null = indefinite)', null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether the hold is currently active')),
                ('released_at', models.DateTimeField(blank=True, help_text='When the hold was released', null=True)),
                ('released_by_id', models.UUIDField(blank=True, help_text='User who released the hold', null=True)),
                ('release_reason', models.TextField(blank=True, help_text='Reason for releasing the hold')),
                ('created_by_id', models.UUIDField(blank=True, help_text='User who created the hold', null=True)),
            ],
            options={
                'verbose_name': 'Retention Exemption',
                'verbose_name_plural': 'Retention Exemptions',
                'db_table': 'retention_exemptions',
                'ordering': ['-hold_start'],
            },
        ),
        migrations.AddIndex(
            model_name='retentionexemption',
            index=models.Index(fields=['resource_type', 'resource_id'], name='retention_exemption_resource_idx'),
        ),
        migrations.AddIndex(
            model_name='retentionexemption',
            index=models.Index(fields=['is_active', 'hold_until'], name='retention_exemption_active_idx'),
        ),

        # =================================================================
        # RETENTION JOB RUNS
        # =================================================================
        migrations.CreateModel(
            name='RetentionJobRun',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('policy', models.ForeignKey(help_text='Policy that was enforced', null=True, on_delete=models.deletion.SET_NULL, related_name='job_runs', to='db.retentionpolicy')),
                ('started_at', models.DateTimeField(auto_now_add=True, help_text='When the job started')),
                ('completed_at', models.DateTimeField(blank=True, help_text='When the job completed', null=True)),
                ('status', models.CharField(choices=[('running', 'Running'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='running', help_text='Current status of the job', max_length=20)),
                ('records_scanned', models.IntegerField(default=0, help_text='Number of records evaluated')),
                ('records_archived', models.IntegerField(default=0, help_text='Number of records archived')),
                ('records_deleted', models.IntegerField(default=0, help_text='Number of records deleted')),
                ('records_exempted', models.IntegerField(default=0, help_text='Number of records skipped due to legal holds')),
                ('error_message', models.TextField(blank=True, help_text='Error message if job failed')),
                ('error_details', models.JSONField(default=dict, help_text='Detailed error information')),
            ],
            options={
                'verbose_name': 'Retention Job Run',
                'verbose_name_plural': 'Retention Job Runs',
                'db_table': 'retention_job_runs',
                'ordering': ['-started_at'],
            },
        ),

        # =================================================================
        # RETENTION ARCHIVES
        # =================================================================
        migrations.CreateModel(
            name='RetentionArchive',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('resource_type', models.CharField(help_text='Type of resource archived', max_length=50)),
                ('resource_id', models.UUIDField(help_text='Original UUID of the archived resource')),
                ('archived_at', models.DateTimeField(auto_now_add=True, help_text='When the record was archived')),
                ('archive_location', models.CharField(blank=True, help_text='S3 path or storage location of archived data', max_length=500)),
                ('archive_checksum', models.CharField(blank=True, help_text='SHA-256 checksum of archived data', max_length=64)),
                ('deleted_at', models.DateTimeField(blank=True, help_text='When the original record was deleted', null=True)),
                ('job_run', models.ForeignKey(help_text='Job run that created this archive', null=True, on_delete=models.deletion.SET_NULL, related_name='archives', to='db.retentionjobrun')),
                ('metadata_snapshot', models.JSONField(default=dict, help_text='Snapshot of key metadata at time of archival')),
            ],
            options={
                'verbose_name': 'Retention Archive',
                'verbose_name_plural': 'Retention Archives',
                'db_table': 'retention_archives',
                'ordering': ['-archived_at'],
            },
        ),
        migrations.AddIndex(
            model_name='retentionarchive',
            index=models.Index(fields=['resource_type', 'resource_id'], name='retention_archive_resource_idx'),
        ),
        migrations.AddIndex(
            model_name='retentionarchive',
            index=models.Index(fields=['archived_at'], name='retention_archive_time_idx'),
        ),
    ]
