# Production security and deployment checklist

This project now applies stronger defaults in the application, but it is not a production deployment by itself. Treat this checklist as a release gate. Do not put real student identity images or high-stakes exams on an internet-facing deployment until every required control below has an owner and a verification record.

## Changes enforced by the application

- API and AI service hide interactive API documentation in production.
- Production configuration rejects weak JWT secrets, wildcard CORS, broad host patterns, long access tokens, non-TLS PostgreSQL URLs, and missing SMTP settings.
- API CORS uses explicit origins, methods, and headers without cookies. Trusted-host checks and browser security headers are enabled.
- Passwords use Argon2id; existing PBKDF2 hashes still verify and are upgraded after a successful login. JWTs use the PyJWT library with HS256 pinned, issuer, audience, issue and expiry times, and a random token ID.
- Login does comparable password-hash work for unknown accounts, and malformed authenticated user IDs return an authentication error.
- Examiner candidate lists and assessment assignments are limited to the examiner's assigned course/year/section groups. Admin-only group changes and roster imports are audited.
- Browser signals and model observations are treated as untrusted client input; production AI rejects synthetic observed detections. Identity threshold is server configuration, not a client option.
- Image inputs are bounded and decoded after format and dimension checks. Evidence names are random, downloads are constrained to the evidence directory, and evidence responses are private and non-cacheable.
- WebSocket credentials are sent through the WebSocket subprotocol rather than query strings. The candidate desktop has a restrictive baseline CSP and frozen prototypes.
- Development PostgreSQL binds to loopback. The compose password is only a local fallback and must never be used in a deployed environment.

## Required before internet-facing deployment

1. **Identity and access:** Replace seed passwords with a real administrator-managed identity provider or secure account lifecycle. Require MFA for administrators and examiners. Apply least-privilege roles, credential recovery, session revocation, and documented account deprovisioning. The current portal has examiner and proctor sign-in only; roster import and examiner group assignment are admin-only API endpoints, so provide a protected admin console or a reviewed administrative client before operational use.
2. **Edge protection:** Put the API behind a maintained HTTPS reverse proxy or API gateway. Enforce shared rate limits for login, account activation, roster upload, identity enrollment, and WebSocket handshakes; cap request bodies, upload sizes, connection counts, and request duration. No shared rate-limit service is currently included in this repository.
3. **Network boundaries:** Keep PostgreSQL and the AI service on private networks. Expose only the HTTPS API and static frontends. Use firewall rules so only the API can call the AI service. The AI endpoints do not authenticate callers and must not be publicly reachable.
4. **Secrets and transport:** Store JWT, SMTP, and database credentials in a managed secret store; rotate them and define emergency revocation. Terminate TLS at the edge and use verified TLS for database connections. Set exact production `CORS_ORIGINS`, `TRUSTED_HOSTS`, `AI_CORS_ORIGINS`, and `AI_TRUSTED_HOSTS` values.
5. **Desktop endpoint policy:** The Tauri CSP currently allows `https:` and `wss:` so an API host can be configured at build time. For each production release, replace those broad schemes with the exact API host and WebSocket host. Keep only the loopback AI endpoint needed by the local candidate app.
6. **Biometric and evidence storage:** Replace local evidence and face-image directories with private encrypted object storage, short-lived authorized downloads, backup/restore testing, a retention schedule, and automated deletion. Define access review and audit export. Set an explicit `IDENTITY_REFERENCE_DIR`/`EVIDENCE_DIR` only for local development; production storage integration is not implemented here.
7. **Database operations:** Run Alembic migrations as a controlled release step, use a managed PostgreSQL service with TLS and private networking, enable encrypted backups, and rehearse restore and migration rollback procedures.
8. **Monitoring and response:** Export structured logs, audit records, and security metrics to a protected system; alert on repeated failed logins, upload spikes, service errors, and unusual admin actions. Define incident response and biometric-data breach procedures. Avoid logging tokens, passwords, face images, or assessment answers.
9. **AI validity and fairness:** Test identity matching and object/face detection across supported cameras, lighting, skin tones, glasses, and accessibility conditions. Tune thresholds on a representative consented validation set. Provide a human appeal/review process. The current client-side inference can be modified or suppressed by a candidate and is evidence for human review, not tamper-proof proof or an automatic misconduct verdict.
10. **Release verification:** Run the API and AI test suites, both frontend production builds, migration tests on the target PostgreSQL version, dependency and secret scans, and end-to-end tests on supported Windows hardware. Test the production origin/CSP configuration before release.

## Configuration notes

Start from `.env.example`, then create deployment-specific secrets outside version control. Production API settings require a database URL such as `postgresql+psycopg://...?...sslmode=verify-full`. Set an explicit host list (hostnames only, no scheme), exact frontend origins, and a 32-character or longer randomly generated `JWT_SECRET`. Set `APP_ENV=production` for both API and AI service. Configure SMTP because account activation depends on email delivery.

Build both frontends with `VITE_API_BASE_URL` set to the final HTTPS API endpoint; production builds fail if that value is missing or non-HTTPS. The candidate desktop calls the local AI sidecar on loopback. Restrict its CSP to the exact deployed API and WebSocket hosts before producing the signed desktop release.

The `docker-compose.yml` file is for local development only. It binds PostgreSQL to `127.0.0.1` and accepts a local fallback password to keep the developer workflow convenient. A real deployment must use managed credentials and infrastructure rather than this Compose service.
