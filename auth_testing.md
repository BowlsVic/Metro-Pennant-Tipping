# Auth Testing Notes

## Accounts
- Admin (password): admin@tipping.com / Admin@123
- Google sign-in (Emergent managed): any Google account. Links to an existing account with the same email (keeps role and tips); otherwise creates a player.
- Apple sign-in: iOS only, needs a real Apple ID on device. Users are keyed by Apple `sub`; linked by verified email if one exists.

## Backend checks
- POST /api/auth/session {session_id} -> 401 for invalid/used ids; on success {session_token, token, user}
- POST /api/auth/apple {identity_token, name?, email?} -> 401 for invalid token; verifies RS256 vs Apple JWKS, iss https://appleid.apple.com, aud in APPLE_AUDIENCES (bundle id + host.exp.Exponent)
- Returned token is the app JWT; use as `Authorization: Bearer <token>` with GET /api/auth/me

## Frontend checks
- Login screen shows "Continue with Google" (testID google-signin-button) on all platforms
- Apple button (apple-signin-button) only renders on iOS devices where Sign in with Apple is available
- Web: Google button navigates to https://auth.emergentagent.com/?redirect=<origin>/ ; returning with #session_id=... is exchanged on load and removed from the URL
- Invalid session_id on return shows an error box (testID auth-error) on the login screen
