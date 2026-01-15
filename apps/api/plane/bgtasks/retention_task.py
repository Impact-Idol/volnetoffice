"""
HIPAA Data Retention Background Tasks

This module provides Celery tasks for enforcing data retention policies,
including archival and deletion of aged data while respecting legal holds.
"""

import hashlib
import json
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger('plane.retention')


# Model mapping for retention processing
RETENTION_MODEL_MAPPING = {
    'attachment': 'plane.db.models.FileAsset',
    'issue': 'plane.db.models.Issue',
    'issue_comment': 'plane.db.models.IssueComment',
    'audit_log': 'plane.db.models.audit.AuditLog',
    'user': 'plane.db.models.User',
    'notification': 'plane.db.models.Notification',
    'session': 'plane.db.models.Session',
    'api_log': 'plane.db.models.APIActivityLog',
    'project': 'plane.db.models.Project',
    'page': 'plane.db.models.Page',
}


def get_model_class(data_type):
    """Import and return the model class for a data type"""
    model_path = RETENTION_MODEL_MAPPING.get(data_type)
    if not model_path:
        return None

    parts = model_path.rsplit('.', 1)
    module_path, class_name = parts[0], parts[1]

    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to import model {model_path}: {e}")
        return None


def check_legal_hold(resource_type, resource_id):
    """Check if a resource is under legal hold"""
    from plane.db.models.retention import RetentionExemption

    return RetentionExemption.objects.filter(
        resource_type=resource_type,
        resource_id=resource_id,
        is_active=True,
    ).filter(
        # Active if no expiry or expiry in future
        models.Q(hold_until__isnull=True) | models.Q(hold_until__gt=timezone.now())
    ).exists()


def create_archive_record(job_run, resource_type, resource_id, data, archive_location=''):
    """Create an archive record for a deleted resource"""
    from plane.db.models.retention import RetentionArchive

    # Create checksum of archived data
    checksum = hashlib.sha256(
        json.dumps(data, sort_keys=True, cls=DjangoJSONEncoder).encode()
    ).hexdigest()

    return RetentionArchive.objects.create(
        job_run=job_run,
        resource_type=resource_type,
        resource_id=resource_id,
        archive_location=archive_location,
        archive_checksum=checksum,
        metadata_snapshot=data,
    )


@shared_task(bind=True, max_retries=3)
def run_retention_job(self, policy_id=None):
    """
    Main retention enforcement task.

    Runs daily to process all active retention policies or a specific policy.

    Args:
        policy_id: Optional UUID of specific policy to run
    """
    from plane.db.models.retention import RetentionPolicy, RetentionJobRun, RetentionExemption
    from plane.utils.audit import create_audit_log
    from django.db import models

    logger.info(f"Starting retention job (policy_id={policy_id})")

    # Get policies to process
    if policy_id:
        policies = RetentionPolicy.objects.filter(id=policy_id, is_active=True)
    else:
        policies = RetentionPolicy.objects.filter(is_active=True)

    if not policies.exists():
        logger.info("No active retention policies to process")
        return {'status': 'skipped', 'reason': 'no_active_policies'}

    results = []

    for policy in policies:
        # Create job run record
        job_run = RetentionJobRun.objects.create(
            policy=policy,
            status='running'
        )

        try:
            result = process_retention_policy(policy, job_run)
            results.append(result)

            # Complete the job run
            job_run.complete(
                status='completed',
            )

            # Log the completion
            create_audit_log(
                action='RETENTION_JOB_COMPLETED',
                resource_type='RetentionPolicy',
                resource_id=policy.id,
                metadata={
                    'job_run_id': str(job_run.id),
                    'records_scanned': job_run.records_scanned,
                    'records_archived': job_run.records_archived,
                    'records_deleted': job_run.records_deleted,
                    'records_exempted': job_run.records_exempted,
                }
            )

        except Exception as e:
            logger.exception(f"Retention job failed for policy {policy.id}")

            job_run.complete(
                status='failed',
                error_message=str(e)
            )

            # Log the failure
            create_audit_log(
                action='RETENTION_JOB_FAILED',
                resource_type='RetentionPolicy',
                resource_id=policy.id,
                metadata={'error': str(e)},
                severity='error'
            )

            # Retry on failure
            raise self.retry(exc=e, countdown=300)  # Retry in 5 minutes

    logger.info(f"Retention job completed. Processed {len(results)} policies.")

    return {
        'status': 'completed',
        'policies_processed': len(results),
        'results': results
    }


def process_retention_policy(policy, job_run):
    """
    Process a single retention policy.

    Args:
        policy: RetentionPolicy instance
        job_run: RetentionJobRun instance for tracking

    Returns:
        Dict with processing results
    """
    from plane.db.models.retention import RetentionExemption
    from django.db import models

    logger.info(f"Processing retention policy: {policy.name} ({policy.data_type})")

    # Get the model class
    model_class = get_model_class(policy.data_type)
    if not model_class:
        logger.warning(f"No model class found for data type: {policy.data_type}")
        return {'status': 'skipped', 'reason': 'no_model_class'}

    # Calculate cutoff date
    cutoff_date = policy.get_cutoff_date()
    logger.info(f"Cutoff date: {cutoff_date}")

    # Build base queryset
    queryset = model_class.objects.filter(created_at__lt=cutoff_date)

    # Filter by workspace if policy is workspace-scoped
    if policy.workspace_id:
        if hasattr(model_class, 'workspace_id'):
            queryset = queryset.filter(workspace_id=policy.workspace_id)
        elif hasattr(model_class, 'project'):
            queryset = queryset.filter(project__workspace_id=policy.workspace_id)

    # Only process soft-deleted records if configured
    if policy.only_archived and hasattr(model_class, 'deleted_at'):
        queryset = queryset.filter(deleted_at__isnull=False)

    # Get count before processing
    total_count = queryset.count()
    job_run.records_scanned = total_count
    job_run.save(update_fields=['records_scanned'])

    logger.info(f"Found {total_count} records eligible for retention processing")

    # Process in batches
    batch_size = 100
    processed = 0
    archived = 0
    deleted = 0
    exempted = 0

    # Get all exemptions for this resource type
    exempted_ids = set(
        RetentionExemption.objects.filter(
            resource_type=policy.data_type,
            is_active=True,
        ).filter(
            models.Q(hold_until__isnull=True) | models.Q(hold_until__gt=timezone.now())
        ).values_list('resource_id', flat=True)
    )

    for record in queryset.iterator(chunk_size=batch_size):
        try:
            # Check for legal hold
            if record.id in exempted_ids:
                logger.debug(f"Skipping {record.id} - under legal hold")
                exempted += 1
                continue

            # Archive if configured
            if policy.archive_before_delete:
                archive_data = {
                    'id': str(record.id),
                    'created_at': record.created_at.isoformat() if hasattr(record, 'created_at') else None,
                }

                # Add model-specific fields
                if hasattr(record, 'name'):
                    archive_data['name'] = record.name
                if hasattr(record, 'description'):
                    archive_data['description'] = record.description[:500] if record.description else None

                create_archive_record(
                    job_run=job_run,
                    resource_type=policy.data_type,
                    resource_id=record.id,
                    data=archive_data
                )
                archived += 1

            # Delete the record (hard delete)
            if hasattr(record, 'delete'):
                record.delete(soft=False)
            deleted += 1

            processed += 1

            # Update job run periodically
            if processed % batch_size == 0:
                job_run.records_archived = archived
                job_run.records_deleted = deleted
                job_run.records_exempted = exempted
                job_run.save(update_fields=['records_archived', 'records_deleted', 'records_exempted'])
                logger.info(f"Processed {processed}/{total_count} records")

        except Exception as e:
            logger.error(f"Error processing record {record.id}: {e}")
            continue

    # Final update
    job_run.records_archived = archived
    job_run.records_deleted = deleted
    job_run.records_exempted = exempted
    job_run.save(update_fields=['records_archived', 'records_deleted', 'records_exempted'])

    logger.info(
        f"Retention policy {policy.name} completed: "
        f"scanned={total_count}, archived={archived}, deleted={deleted}, exempted={exempted}"
    )

    return {
        'policy_id': str(policy.id),
        'policy_name': policy.name,
        'records_scanned': total_count,
        'records_archived': archived,
        'records_deleted': deleted,
        'records_exempted': exempted,
    }


@shared_task
def check_expired_legal_holds():
    """
    Check for and deactivate expired legal holds.

    Runs daily to clean up holds that have passed their expiration date.
    """
    from plane.db.models.retention import RetentionExemption
    from plane.utils.audit import create_audit_log

    logger.info("Checking for expired legal holds")

    expired_holds = RetentionExemption.objects.filter(
        is_active=True,
        hold_until__isnull=False,
        hold_until__lt=timezone.now()
    )

    count = 0
    for hold in expired_holds:
        hold.is_active = False
        hold.released_at = timezone.now()
        hold.release_reason = 'Automatic expiration'
        hold.save()

        create_audit_log(
            action='LEGAL_HOLD_EXPIRED',
            resource_type=hold.resource_type,
            resource_id=hold.resource_id,
            metadata={
                'exemption_id': str(hold.id),
                'hold_until': hold.hold_until.isoformat(),
            }
        )

        count += 1

    logger.info(f"Deactivated {count} expired legal holds")

    return {'expired_holds_released': count}


@shared_task
def generate_retention_report(workspace_id=None, email_to=None):
    """
    Generate a retention compliance report.

    Args:
        workspace_id: Optional workspace to scope the report
        email_to: Email address to send the report
    """
    from plane.db.models.retention import RetentionPolicy, RetentionJobRun, RetentionExemption

    logger.info(f"Generating retention report (workspace_id={workspace_id})")

    report_data = {
        'generated_at': timezone.now().isoformat(),
        'workspace_id': str(workspace_id) if workspace_id else 'global',
        'policies': [],
        'active_holds': [],
        'recent_job_runs': [],
    }

    # Get policies
    policies = RetentionPolicy.objects.filter(is_active=True)
    if workspace_id:
        policies = policies.filter(
            models.Q(workspace_id=workspace_id) | models.Q(workspace_id__isnull=True)
        )

    for policy in policies:
        report_data['policies'].append({
            'name': policy.name,
            'data_type': policy.data_type,
            'retention_days': policy.retention_days,
            'archive_before_delete': policy.archive_before_delete,
        })

    # Get active holds
    holds = RetentionExemption.objects.filter(is_active=True)
    for hold in holds[:50]:  # Limit to 50
        report_data['active_holds'].append({
            'resource_type': hold.resource_type,
            'resource_id': str(hold.resource_id),
            'reason': hold.reason,
            'hold_until': hold.hold_until.isoformat() if hold.hold_until else 'indefinite',
        })

    # Get recent job runs
    job_runs = RetentionJobRun.objects.order_by('-started_at')[:10]
    for run in job_runs:
        report_data['recent_job_runs'].append({
            'policy_name': run.policy.name if run.policy else 'Unknown',
            'started_at': run.started_at.isoformat(),
            'status': run.status,
            'records_deleted': run.records_deleted,
            'records_exempted': run.records_exempted,
        })

    logger.info("Retention report generated successfully")

    # Email the report if requested
    if email_to:
        from django.core.mail import send_mail

        send_mail(
            subject='HIPAA Data Retention Compliance Report',
            message=json.dumps(report_data, indent=2),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email_to],
            fail_silently=True,
        )

    return report_data
