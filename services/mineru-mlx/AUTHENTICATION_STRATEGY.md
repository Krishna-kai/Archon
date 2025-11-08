# Authentication Strategy for MinerU-MLX OCR Service

## Current State

**Service**: MinerU-MLX PDF OCR and Structured Extraction
**URL**: http://localhost:9006
**Status**: Single-user local deployment
**Authentication**: None

---

## Requirements

### Use Cases

1. **AI Undecided Website**: Public users need OCR access
2. **Mahinda University**: Research team collaboration
3. **API Access**: Programmatic access with rate limiting
4. **Usage Tracking**: Monitor extractions per user
5. **Quota Management**: Prevent abuse

---

## Authentication Options Analysis

### Option 1: Google Single Sign-On (SSO) ⭐ RECOMMENDED

**Implementation**:
```python
# FastAPI with authlib
from authlib.integrations.fastapi_client import OAuth

oauth = OAuth()
oauth.register(
    'google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get('/login/google')
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_google')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get('/auth/google')
async def auth_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get('userinfo')
    # Create/update user in database
    return user
```

**Setup Requirements**:
1. Create Google Cloud Project
2. Enable Google OAuth 2.0
3. Configure authorized redirect URIs
4. Get client ID and secret

**Pros**:
- ✅ 90% of users have Google accounts
- ✅ No password management
- ✅ Trusted by universities
- ✅ Easy to implement
- ✅ Free for unlimited users

**Cons**:
- ⚠️ Requires Google account
- ⚠️ User data tied to Google

**Best For**: AI Undecided, university collaboration, research teams

---

### Option 2: GitHub OAuth

**Implementation**:
```python
oauth.register(
    'github',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

@app.get('/login/github')
async def login_github(request: Request):
    redirect_uri = request.url_for('auth_github')
    return await oauth.github.authorize_redirect(request, redirect_uri)
```

**Setup Requirements**:
1. Create GitHub OAuth App
2. Configure callback URL
3. Get client ID and secret

**Pros**:
- ✅ Developer-friendly
- ✅ Many devs have GitHub
- ✅ Free for public repos
- ✅ Good for open-source

**Cons**:
- ⚠️ Not all researchers have GitHub
- ⚠️ Less familiar to non-devs

**Best For**: Developer tools, API-first services

---

### Option 3: Email/Password (Traditional)

**Implementation**:
```python
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Setup Requirements**:
1. Implement password hashing
2. Email verification system
3. Password reset flow
4. Security best practices

**Pros**:
- ✅ Full control
- ✅ No third-party dependencies
- ✅ Works for everyone

**Cons**:
- ❌ Password management burden
- ❌ Security responsibility
- ❌ Email verification needed
- ❌ Password reset complexity

**Best For**: Enterprise, high-security requirements

---

## RECOMMENDED STRATEGY: Multi-Provider OAuth

### Primary: Google SSO (90% of users)
### Secondary: GitHub OAuth (developers)
### Fallback: Email/Password (privacy-conscious users)

---

## Implementation Plan

### Phase 1: Database Schema (Supabase)

```sql
-- Users table
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  full_name TEXT,
  avatar_url TEXT,

  -- Auth provider info
  auth_provider TEXT NOT NULL, -- 'google', 'github', 'email'
  auth_provider_id TEXT, -- OAuth provider user ID
  password_hash TEXT, -- Only for email/password users
  email_verified BOOLEAN DEFAULT FALSE,

  -- API access
  api_key TEXT UNIQUE, -- For programmatic access
  api_key_created_at TIMESTAMPTZ,

  -- Usage tracking
  usage_quota JSONB DEFAULT '{"daily": 100, "monthly": 1000}'::jsonb,
  usage_current JSONB DEFAULT '{"daily": 0, "monthly": 0}'::jsonb,
  last_usage_reset TIMESTAMPTZ DEFAULT NOW(),

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ,
  is_active BOOLEAN DEFAULT TRUE,
  is_admin BOOLEAN DEFAULT FALSE
);

-- Extraction history
CREATE TABLE extraction_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,

  -- Extraction details
  pdf_filename TEXT NOT NULL,
  pdf_size_bytes BIGINT,
  template_used TEXT NOT NULL,
  model_used TEXT NOT NULL,

  -- Results
  processing_time_seconds FLOAT,
  success BOOLEAN NOT NULL,
  error_message TEXT,
  extracted_fields_count INT,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  ip_address INET
);

-- API keys (separate table for revocation)
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  key_hash TEXT UNIQUE NOT NULL,
  key_prefix TEXT NOT NULL, -- First 8 chars for display
  name TEXT, -- User-defined key name
  scopes JSONB DEFAULT '["read", "extract"]'::jsonb,
  last_used TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  is_active BOOLEAN DEFAULT TRUE
);

-- Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);
CREATE INDEX idx_extraction_history_user ON extraction_history(user_id);
CREATE INDEX idx_extraction_history_created ON extraction_history(created_at);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);
```

### Phase 2: FastAPI Authentication

**Dependencies**:
```bash
pip install authlib python-jose[cryptography] passlib[bcrypt] python-multipart
```

**File**: `auth.py`
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

security = HTTPBearer()

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication")

async def get_current_active_user(user_id: str = Depends(get_current_user)):
    # Fetch user from Supabase
    # Check if user is active
    # Return user object
    return user_id

async def check_quota(user_id: str = Depends(get_current_active_user)):
    # Check daily/monthly quota
    # Increment usage counter
    # Raise exception if exceeded
    pass
```

**File**: `app.py` (modified)
```python
from fastapi import FastAPI, Depends, File, UploadFile
from auth import get_current_active_user, check_quota

app = FastAPI()

# Public endpoints (no auth)
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Protected endpoints
@app.post("/process")
async def process_pdf(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_active_user),
    _quota: None = Depends(check_quota)
):
    # Existing PDF processing logic
    # Log extraction to history
    pass

@app.post("/extract-structured")
async def extract_structured(
    request: ExtractionRequest,
    user_id: str = Depends(get_current_active_user),
    _quota: None = Depends(check_quota)
):
    # Existing extraction logic
    # Log to history
    pass
```

### Phase 3: OAuth Routes

**File**: `oauth_routes.py`
```python
from fastapi import APIRouter, Request
from authlib.integrations.fastapi_client import OAuth
from auth import create_access_token

router = APIRouter()
oauth = OAuth()

# Google OAuth
oauth.register(
    'google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@router.get('/login/google')
async def login_google(request: Request):
    redirect_uri = f"{request.base_url}auth/google"
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get('/auth/google')
async def auth_google(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user = token.get('userinfo')

    # Create or update user in Supabase
    # user_id = create_or_update_user(user, 'google')

    # Create JWT token
    access_token = create_access_token({"sub": user['email']})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

# GitHub OAuth
oauth.register(
    'github',
    client_id=os.getenv('GITHUB_CLIENT_ID'),
    client_secret=os.getenv('GITHUB_CLIENT_SECRET'),
    authorize_url='https://github.com/login/oauth/authorize',
    access_token_url='https://github.com/login/oauth/access_token',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

@router.get('/login/github')
async def login_github(request: Request):
    redirect_uri = f"{request.base_url}auth/github"
    return await oauth.github.authorize_redirect(request, redirect_uri)

@router.get('/auth/github')
async def auth_github(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get('user', token=token)
    user = resp.json()

    # Create or update user
    # user_id = create_or_update_user(user, 'github')

    access_token = create_access_token({"sub": user['email']})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }
```

### Phase 4: Frontend Integration

**Updated**: `mineru_ui.html`
```html
<!-- Add login buttons -->
<div id="auth-section" style="margin-bottom: 20px;">
    <div id="logged-out" style="display: none;">
        <h3>Sign In</h3>
        <button onclick="loginWithGoogle()">Sign in with Google</button>
        <button onclick="loginWithGitHub()">Sign in with GitHub</button>
    </div>

    <div id="logged-in" style="display: none;">
        <p>Welcome, <span id="user-name"></span>!</p>
        <p>Quota: <span id="quota-used"></span> / <span id="quota-limit"></span> extractions today</p>
        <button onclick="logout()">Logout</button>
    </div>
</div>

<script>
let accessToken = localStorage.getItem('access_token');

function loginWithGoogle() {
    window.location.href = '/login/google';
}

function loginWithGitHub() {
    window.location.href = '/login/github';
}

function logout() {
    localStorage.removeItem('access_token');
    location.reload();
}

// Add token to API requests
async function uploadPDF() {
    const formData = new FormData();
    formData.append('file', document.getElementById('pdfFile').files[0]);

    const response = await fetch('/process', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${accessToken}`
        },
        body: formData
    });

    // Handle response...
}
</script>
```

---

## Deployment Considerations

### Environment Variables

```bash
# .env file
JWT_SECRET_KEY=your-super-secret-key-change-me
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-key
```

### Rate Limiting

**Default Quotas**:
- **Free Tier**: 10 extractions/day, 100/month
- **Registered**: 100 extractions/day, 1000/month
- **Premium**: Unlimited

**Implementation**:
```python
from datetime import datetime

async def check_quota(user_id: str):
    # Get user quota from database
    user = get_user(user_id)

    # Reset counters if new day/month
    if should_reset_daily(user):
        reset_daily_quota(user_id)
    if should_reset_monthly(user):
        reset_monthly_quota(user_id)

    # Check limits
    if user.usage_current['daily'] >= user.usage_quota['daily']:
        raise HTTPException(429, "Daily quota exceeded")
    if user.usage_current['monthly'] >= user.usage_quota['monthly']:
        raise HTTPException(429, "Monthly quota exceeded")

    # Increment counter
    increment_usage(user_id)
```

---

## Testing Strategy

### Unit Tests
```python
def test_google_oauth_flow():
    # Mock Google OAuth response
    # Test user creation
    # Verify JWT token generation
    pass

def test_quota_enforcement():
    # Create user with quota
    # Make requests until quota exceeded
    # Verify 429 error
    pass

def test_api_key_access():
    # Create API key
    # Use key in Authorization header
    # Verify access
    pass
```

### Integration Tests
- Test login flow with real OAuth providers (dev environment)
- Test quota reset at midnight
- Test API key revocation

---

## Migration Path

### Step 1: Add Authentication (Backward Compatible)
- Keep existing endpoints working
- Add optional authentication
- No breaking changes

### Step 2: Gradual Enforcement
- Warn users about upcoming auth requirement
- Give 30-day grace period
- Track unauthenticated usage

### Step 3: Full Enforcement
- Require authentication for all endpoints
- Migrate existing users
- Provide migration guide

---

## Recommended Timeline

**Week 1**: Database schema + Google OAuth
**Week 2**: GitHub OAuth + JWT tokens
**Week 3**: Quota system + usage tracking
**Week 4**: Frontend integration + testing
**Week 5**: Documentation + deployment

---

## Cost Analysis

**Google Cloud Platform**: FREE (OAuth 2.0 is free)
**GitHub OAuth**: FREE
**Supabase**: FREE tier covers 50K users
**FastAPI/Python**: FREE (open-source)

**Total Cost**: $0 for up to 50K users

---

## Security Considerations

1. **HTTPS Required**: OAuth redirects require HTTPS
2. **JWT Secret**: Use cryptographically secure random string
3. **Token Expiry**: 24-hour access tokens, 30-day refresh tokens
4. **Rate Limiting**: Prevent brute force attacks
5. **API Key Rotation**: Allow users to regenerate keys
6. **Audit Logging**: Track all auth events

---

## Next Steps

1. **Create Google Cloud Project** (15 minutes)
2. **Create GitHub OAuth App** (5 minutes)
3. **Implement database schema** (1 hour)
4. **Add authentication middleware** (2 hours)
5. **Update frontend UI** (2 hours)
6. **Testing** (4 hours)
7. **Deploy to production** (2 hours)

**Total Effort**: ~1-2 days for basic implementation

---

**Created**: 2025-11-08
**Status**: Planning Complete - Ready for Implementation
**Recommended**: Multi-provider OAuth (Google + GitHub + Email)
**Timeline**: 5 weeks for full rollout
