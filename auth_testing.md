# Auth-Gated App Testing Playbook (Emergent Google Auth)

NOTE: Do not be satisfied until you've tested the app completely, especially the auth-gated pages.
Use the app's REAL database (MONGO_URL / DB_NAME from backend/.env), NOT `test_database`.

## Step 1: Create Test User & Session (inject directly into Mongo)
```
mongosh "<MONGO_URL>/<DB_NAME>" --eval "
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  role: 'visitor',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```
# Auth endpoint (cookie OR bearer header)
curl -X GET "$API/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Guardian-only example (Phase 2)
curl -X GET "$API/api/codon-forge/..." -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing (Playwright)
```
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "<app-domain>",
    "path": "/",
    "httpOnly": True,
    "secure": True,
    "sameSite": "None"
}])
await page.goto("<app-url>")
```

## Guardian role
- Guardian accounts are designated by EMAIL via `GUARDIAN_EMAILS` (backend env/config).
- Current Guardian: davebouchez@gmail.com
- Everyone else defaults to `visitor`.

## Checklist
- User doc has custom `user_id` field; all queries use `{"_id": 0}` projection.
- Session `user_id` matches user's `user_id` exactly.
- `/api/auth/me` returns user data (not 401) with valid token.
- App loads main view (not login) when authenticated; redirects to login when not.

## Notes
- Google OAuth consent must be completed at the TOP-LEVEL URL (new tab), not inside the preview iframe.
- Do NOT store passwords for Google Auth (OAuth has none). Save test identities/roles to /app/memory/test_credentials.md.
