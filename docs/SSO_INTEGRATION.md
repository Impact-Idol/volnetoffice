# External SSO Integration

**Status:** Production Ready
**Version:** 1.0.0

---

## Overview

VolNetOffice supports external SSO integration via JWT token exchange. This allows seamless authentication from external identity providers without requiring users to maintain separate credentials.

## Architecture

```
┌─────────────────┐         JWT Token          ┌──────────────────┐
│                 │ ─────────────────────────> │                  │
│  External App   │                             │  VolNetOffice    │
│  (IdP)          │ <───────────────────────── │  (Service        │
│                 │    Session Cookie (HTTPS)   │   Provider)      │
└─────────────────┘                             └──────────────────┘
```

## Features

- ✅ JWT token-based authentication
- ✅ Automatic user provisioning
- ✅ Role mapping and workspace assignment
- ✅ Session-based authentication with secure cookies
- ✅ HIPAA-compliant session management
- ✅ Comprehensive audit logging

---

## Implementation

### Backend SSO Endpoint

**Location:** `apps/api/plane/authentication/views/sso.py`

**Endpoint:** `POST /auth/impactidol-sso/`

**Features:**
- Validates JWT tokens signed with shared secret
- Creates user accounts on first login
- Automatically creates user Profile
- Syncs users to workspace with role mapping
- Establishes Django session

### Frontend SSO Handler

**Location:** `apps/web/app/(all)/sso/page.tsx`

**Route:** `/sso?token=<jwt>`

**Flow:**
1. Extracts JWT token from URL query parameter
2. Calls backend SSO endpoint
3. Receives session cookie
4. Redirects to workspace

---

## Configuration

### Environment Variables

```bash
# SSO Configuration
IMPACTIDOL_JWT_SECRET=your-shared-secret-here
IMPACTIDOL_SERVICE_TOKEN=service-to-service-token
DEFAULT_WORKSPACE_SLUG=default-workspace

# CORS (adjust for your domain)
CORS_ALLOWED_ORIGINS=https://your-frontend-url.com

# Session Security
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_AGE=900  # 15 minutes
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
```

### JWT Token Format

The external application must generate JWT tokens with the following payload:

```json
{
  "sub": "user-id",
  "email": "user@example.com",
  "name": "User Display Name",
  "role": "USER_ROLE",
  "status": "ACTIVE",
  "iat": 1234567890,
  "exp": 1234568190
}
```

**Required Fields:**
- `sub` - Unique user identifier
- `email` - User's email address
- `name` - User's display name
- `role` - User's role (must be in `ALLOWED_ROLES`)
- `status` - Account status (must be "ACTIVE")
- `exp` - Token expiration timestamp

### Role Mapping

Configure role mapping in `sso.py`:

```python
ALLOWED_ROLES = frozenset([
    "STAFF",
    "ADMIN",
    "MANAGER",
    # Add your roles here
])

ROLE_MAPPING = {
    "ADMIN": 20,      # VolNetOffice Admin
    "MANAGER": 15,    # VolNetOffice Member
    "STAFF": 15,      # VolNetOffice Member
}
```

---

## Security Considerations

### Token Security

- ✅ Tokens must be signed with HS256 algorithm
- ✅ Short expiration times recommended (5 minutes)
- ✅ Shared secret must be stored securely (environment variable)
- ✅ Token validation includes signature and expiration checks

### Session Security

- ✅ Secure cookies (HTTPS only)
- ✅ HttpOnly cookies (XSS protection)
- ✅ SameSite=Lax (CSRF protection)
- ✅ Automatic session expiry on browser close
- ✅ Inactivity timeout (configurable)

### Audit Logging

All SSO authentication attempts are logged:

```python
logger.info(f"SSO: User {email} authenticated")
logger.warning(f"SSO auth failed: {reason}")
```

---

## Integration Steps

### 1. External Application Setup

Your external application needs to:

1. Generate JWT tokens signed with shared secret
2. Redirect users to: `https://your-volnetoffice-url/sso?token=<jwt>`
3. Handle SSO failures gracefully

**Example Token Generation (Node.js):**

```typescript
import jwt from 'jsonwebtoken';

const ssoToken = jwt.sign(
  {
    sub: user.id,
    email: user.email,
    name: user.name,
    role: user.role,
    status: user.status,
    iat: Math.floor(Date.now() / 1000),
    exp: Math.floor(Date.now() / 1000) + 300  // 5 min
  },
  process.env.SSO_JWT_SECRET,
  { algorithm: 'HS256' }
);

const ssoUrl = `${VOLNETOFFICE_URL}/sso?token=${ssoToken}`;
```

### 2. VolNetOffice Setup

1. **Configure Environment Variables:**
   ```bash
   IMPACTIDOL_JWT_SECRET=<shared-secret>
   DEFAULT_WORKSPACE_SLUG=<workspace-slug>
   CORS_ALLOWED_ORIGINS=<your-app-url>
   ```

2. **Create Default Workspace:**
   ```bash
   # Through Django admin or API
   python manage.py shell
   >>> from plane.db.models import Workspace
   >>> Workspace.objects.create(
   ...     name="Default Workspace",
   ...     slug="default-workspace"
   ... )
   ```

3. **Test SSO Flow:**
   - Generate test JWT token
   - Navigate to `/sso?token=<jwt>`
   - Verify session creation and workspace access

---

## Customization

### Custom User Fields

To sync additional user fields during SSO:

```python
# In apps/api/plane/authentication/views/sso.py

user, created = User.objects.get_or_create(
    email=email,
    defaults={
        'first_name': extract_first_name(name),
        'last_name': extract_last_name(name),
        'display_name': name,
        'is_active': True,
        'is_email_verified': True,
        # Add custom fields:
        'department': payload.get('department'),
        'employee_id': payload.get('employee_id'),
    }
)
```

### Custom Workspace Assignment

To assign users to workspaces based on custom logic:

```python
def _sync_user_to_workspace(self, user, role: str):
    # Custom logic for workspace selection
    workspace_slug = self._get_workspace_for_user(user, role)
    workspace = Workspace.objects.filter(slug=workspace_slug).first()

    if workspace:
        WorkspaceMember.objects.update_or_create(
            workspace=workspace,
            member=user,
            defaults={'role': ROLE_MAPPING.get(role, 5), 'is_active': True}
        )
```

---

## Troubleshooting

### Issue: 401 Unauthorized

**Cause:** Invalid token signature or expired token

**Solution:**
- Verify shared secret matches in both applications
- Check token expiration time
- Review logs: `docker logs volnetoffice-api | grep "SSO"`

### Issue: 403 Forbidden

**Cause:** User role not allowed or account not active

**Solution:**
- Verify user role is in `ALLOWED_ROLES`
- Check user status is "ACTIVE"
- Review role mapping configuration

### Issue: Session cookie not set

**Cause:** Missing Profile object or session creation failure

**Solution:**
- Profile is automatically created in current implementation
- Check `SESSION_COOKIE_SECURE` matches protocol (HTTPS)
- Verify `credentials: "include"` in frontend fetch call

---

## API Reference

### POST /auth/impactidol-sso/

**Request:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "First",
    "last_name": "Last",
    "display_name": "First Last"
  }
}
```

**Headers:**
```
Set-Cookie: session-id=<session-key>; Secure; HttpOnly; SameSite=Lax
```

**Error Responses:**

- `400` - Missing or invalid token
- `401` - Token expired or invalid signature
- `403` - Insufficient permissions or inactive account
- `500` - Server configuration error

---

## Testing

### Manual Test

```bash
# Generate test token (Python)
import jwt
import time

token = jwt.encode({
    'sub': 'test-user-123',
    'email': 'test@example.com',
    'name': 'Test User',
    'role': 'STAFF',
    'status': 'ACTIVE',
    'iat': int(time.time()),
    'exp': int(time.time()) + 300
}, 'your-shared-secret', algorithm='HS256')

print(f"https://your-volnetoffice/sso?token={token}")
```

### Automated Test

```bash
# Test SSO endpoint
curl -X POST https://your-volnetoffice/api/auth/impactidol-sso/ \
  -H "Content-Type: application/json" \
  -d '{"token":"<jwt-token>"}' \
  -v
```

---

## License

This SSO integration is part of VolNetOffice and follows the same license as the main project.

---

## Support

For issues or questions about SSO integration:
- Open an issue on GitHub
- Check existing documentation
- Review audit logs for authentication events

---

**Last Updated:** January 15, 2026
