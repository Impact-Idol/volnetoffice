# Archived: Standalone VolNetOffice Deployment

This directory contains the archived standalone Plane/VolNetOffice deployment configuration.

## What is this?

This was the original development environment for testing Plane/VolNetOffice independently, before it was integrated with Impact Idol.

## Contents

- `docker-compose.standalone.yml` - Full Plane deployment with all components
- `.env.standalone` - Environment configuration for standalone deployment

## Components Included

- **web** - Main Plane web app
- **admin** - God-mode admin interface
- **space** - Public space interface
- **api** - Backend API server
- **proxy** - Caddy reverse proxy
- **worker** - Background job processing
- **beat-worker** - Scheduled task processing
- **live** - Real-time collaboration service
- **migrator** - Database migrations

## Why was it archived?

The standalone deployment was replaced by the integrated deployment in `/docker-compose.employee-portal.yml`, which includes:
- Impact Idol main app
- VolNetOffice employee portal (web frontend only)
- SSO integration between Impact Idol and VolNetOffice

Running both deployments simultaneously caused conflicts and resource issues.

## How to use (if needed)

If you need to run the standalone Plane deployment for testing:

```bash
cd /Users/pushkar/Downloads/newvms80/impact-idol/volnetoffice
docker-compose -f archive/docker-compose.standalone.yml up -d
```

**Warning:** Make sure the integrated deployment is stopped first to avoid port conflicts:
```bash
docker-compose -f ../docker-compose.employee-portal.yml down
```

## Current Production Setup

Use the integrated deployment instead:
```bash
cd /Users/pushkar/Downloads/newvms80/impact-idol
docker-compose -f docker-compose.employee-portal.yml up -d
```

This provides:
- Impact Idol at http://localhost:4500
- Employee Portal at https://localhost:3443 (with SSO)

---
*Archived on: January 15, 2026*
