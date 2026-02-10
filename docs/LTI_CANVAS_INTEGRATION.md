# LTI 1.3 Integration: SpeechGradebook in Canvas

This guide explains how to add SpeechGradebook as an LTI tool in Canvas (or other LMS) so it can appear alongside Achieve in the same course.

## Overview

- **Goal**: SpeechGradebook appears as an external tool in Canvas courses; students and instructors access it from within their course.
- **Flow**: Canvas → LTI launch → SpeechGradebook (with user context: name, email, course, role)
- **Result**: Achieve (textbook) and SpeechGradebook (evaluations) are both in the same course.

---

## Part 1: SpeechGradebook Implementation

### 1.1 Add LTI 1.3 endpoints to the backend

SpeechGradebook uses FastAPI (`app.py`). Add these routes:

| Endpoint | Purpose |
|----------|---------|
| `GET /lti/login` | OIDC login initiation – Canvas redirects here with login_hint, etc. |
| `POST /lti/launch` | Launch endpoint – Canvas POSTs the LTI message here; validate JWT and redirect to app |
| `GET /lti/jwks` | JWKS URL – Canvas fetches your public key to verify signatures |

### 1.2 Use PyLTI1p3

Add the Python library:

```text
PyLTI1p3>=1.10.0
```

PyLTI1p3 handles OIDC login, JWT validation, and launch message parsing.

### 1.3 Generate RSA key pair

LTI 1.3 uses RS256. Generate a key pair:

```bash
openssl genrsa -out lti_private.key 2048
openssl rsa -in lti_private.key -pubout -out lti_public.key
```

Store the private key securely (env var or secret manager). Expose the public key via `/lti/jwks`.

### 1.4 Launch flow

1. Instructor adds "SpeechGradebook" as External Tool in a Canvas module.
2. Student clicks the link → Canvas redirects to your `/lti/login` with OIDC params.
3. Your app redirects back to Canvas's auth URL.
4. Canvas POSTs the LTI launch message to `/lti/launch`.
5. Your app validates the JWT, extracts user/course/role, and either:
   - Redirects to the main app with an LTI session token, or
   - Embeds the app in an iframe and passes context via postMessage.

### 1.5 User context from LTI

The launch message includes:

- `name`, `email` (or `lis_person_contact_email_primary`)
- `https://purl.imsglobal.org/spec/lti/claim/roles` (e.g. Instructor, Learner)
- `https://purl.imsglobal.org/spec/lti/claim/context` (course title, id)
- `https://purl.imsglobal.org/spec/lti/claim/resource_link` (resource link id)

Use this to auto-login or pre-populate the user in SpeechGradebook (or sync with Supabase auth).

---

## Part 2: Canvas (UTK) Configuration

### 2.1 Admin adds SpeechGradebook as a Developer Key (LTI 1.3)

A Canvas admin (or IMS Admin) creates an LTI 1.3 Developer Key:

1. **Admin** → **Developer Keys** → **+ Developer Key** → **+ LTI Key**
2. Set:
   - **Key Name**: SpeechGradebook
   - **Owner Email**: your contact
   - **Redirect URI**: `https://speechgradebook.onrender.com/lti/launch` (or your production URL)
   - **JWK Method**: Public JWK URL  
   - **Public JWK URL**: `https://speechgradebook.onrender.com/lti/jwks`
   - **LTI 1.3 Login URL**: `https://speechgradebook.onrender.com/lti/login`

3. Enable the key and copy the **Client ID** (you may need this in your app config).

### 2.2 Add as External Tool in a course

1. In a Canvas course, go to **Modules** (or Settings → Apps).
2. **+ Add** → **External Tool**.
3. Either select "SpeechGradebook" if configured at account level, or enter:
   - **URL**: `https://speechgradebook.onrender.com/lti/login` (or the Client ID will look up the config)
   - **Open in new tab** (optional; launching in iframe is common).

### 2.3 Achieve in the same course

Achieve is added via the VitalSource LTI tool (already configured at UTK). Students see both:

- Macmillan Achieve (from VitalSource)
- SpeechGradebook (from your LTI tool)

in the same course.

---

## Part 3: SpeechGradebook ↔ Supabase Auth

You have two main options:

### Option A: LTI-only session (simplest)

- On successful launch, create a temporary session (e.g. JWT or signed cookie) with user info from LTI.
- SpeechGradebook treats this as "LTI user" – no Supabase login. Courses/rosters would come from LTI context or need to be synced separately.
- **Limitation**: Your current app is built around Supabase auth and `user_profiles`. LTI users wouldn't have a `user_profiles` row unless you create one.

### Option B: Link LTI to Supabase (recommended)

- On launch, match the LTI email to an existing Supabase user (or create one).
- Log the user in via Supabase (e.g. magic link or existing session if they've used SpeechGradebook before).
- Continue to use existing `user_profiles`, `courses`, etc. LTI becomes another way to *access* the app, not a separate auth system.

**Recommendation**: Option B. Add an LTI launch handler that:
1. Validates the LTI JWT.
2. Looks up or creates a Supabase user by email.
3. Establishes a Supabase session (or redirects to a signed URL that does).
4. Redirects to the main app with that session.

---

## Part 4: Implementation Order

1. **Phase 1 – LTI endpoints**
   - Add `/lti/login`, `/lti/launch`, `/lti/jwks` to `app.py`.
   - Use PyLTI1p3 to handle OIDC and launch.
   - Generate and wire up RSA keys.
   - On launch, log the LTI payload (for debugging) and redirect to `index.html` with a minimal query param like `?lti=1`.

2. **Phase 2 – Canvas configuration**
   - Create Developer Key in Canvas (or have UTK admin do it).
   - Add SpeechGradebook as an external tool in a test course.
   - Confirm launch works and you receive valid JWT + user/context.

3. **Phase 3 – Auth integration**
   - Implement Option B: map LTI user to Supabase user.
   - Ensure LTI-launched users get a valid session and see the right courses/data.

4. **Phase 4 – Optional**
   - Deep linking (pre-fill course/assignment from LTI).
   - Assignments & Grades: send grades back to Canvas (optional; more involved).

---

## Part 5: Per-institution configuration

When you add more institutions:

- Each institution configures SpeechGradebook in their own Canvas/LMS using the same tool URL and JWKS.
- Your app is one deployment; the LTI launch message includes a platform `iss` (issuer) and `client_id`, so you can distinguish Canvas instances if needed.
- Store `institution_id` mapping by LTI `iss` + `client_id` (or domain) if you want institution-specific behavior.

---

## References

- [PyLTI1p3](https://github.com/dmitry-viskov/pylti1.3) – Python LTI 1.3 library
- [PyLTI1p3 Flask Example](https://github.com/dmitry-viskov/pylti1.3-flask-example) – adapt for FastAPI
- [Canvas LTI 1.3 Developer Key setup](https://community.canvaslms.com/t5/Admin-Guide/How-do-I-configure-an-LTI-key-for-an-application/ta-p/62453)
- [IMS LTI 1.3 Core spec](https://www.imsglobal.org/spec/lti/v1p3)
