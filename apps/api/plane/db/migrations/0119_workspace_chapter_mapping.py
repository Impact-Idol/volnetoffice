# Generated migration for Workspace Chapter Mapping
# Sprint 7: Permissions System

import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0118_hipaa_password_security'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkspaceChapterMapping',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True, db_index=True)),
                ('chapter_id', models.CharField(
                    blank=True,
                    db_index=True,
                    help_text='Primary Impact Idol chapter ID linked to this workspace',
                    max_length=255,
                    null=True
                )),
                ('chapter_name', models.CharField(
                    blank=True,
                    help_text='Chapter name for display purposes',
                    max_length=255,
                    null=True
                )),
                ('workspace_type', models.CharField(
                    choices=[
                        ('org', 'Organization-wide'),
                        ('chapter', 'Chapter-specific'),
                        ('cross', 'Cross-chapter')
                    ],
                    default='org',
                    help_text='Type of workspace for permission scoping',
                    max_length=20
                )),
                ('additional_chapter_ids', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='Additional chapter IDs for cross-chapter workspaces'
                )),
                ('workspace', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='chapter_mapping',
                    to='db.workspace'
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='%(class)s_created_by',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Created By'
                )),
                ('updated_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='%(class)s_updated_by',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Updated By'
                )),
            ],
            options={
                'verbose_name': 'Workspace Chapter Mapping',
                'verbose_name_plural': 'Workspace Chapter Mappings',
                'db_table': 'workspace_chapter_mappings',
                'ordering': ('-created_at',),
            },
        ),
        # Add index for chapter_id lookups
        migrations.AddIndex(
            model_name='workspacechaptermapping',
            index=models.Index(
                fields=['chapter_id', 'workspace_type'],
                name='ws_chapter_mapping_ch_type_idx'
            ),
        ),
    ]
