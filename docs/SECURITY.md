# Security Documentation

## 1. Security Scope

This document describes the security posture of the current ZonalHub implementation and a hardening roadmap for production deployment.

Current state:
- internal/trusted-network oriented MVP
- no authentication yet
- no authorization layers yet

## 2. Assets to Protect

Primary assets:
- Zonal data integrity (`zonal_values`)
- Dataset lineage and provenance metadata
- Database credentials and environment secrets
- Service availability for B2B users

Secondary assets:
- Downloaded BIR source files and manifests
- Operational logs and deployment scripts

## 3. Trust Boundaries

- Browser client to API boundary
- API service to database boundary
- Ingestion scripts to external BIR endpoints boundary
- Local/CI environment to production boundary

## 4. Current Security Controls

Implemented controls:
- SQLAlchemy ORM parameterization (reduces SQL injection risk from query params)
- FastAPI request parsing/validation for typed query inputs
- Config via environment variables (`.env`)
- CORS allowlist configurable through settings
- Source lineage fields for record-level auditability

Database controls (recommended deployment baseline):
- dedicated DB user with least privilege
- network restriction to API host(s)

## 5. Current Gaps

High-priority gaps:
- No authentication or session/token validation
- No authorization or role-based access control
- No API rate limiting or abuse controls
- No audit trail for data read actions
- No request correlation IDs and structured security logs
- No automated secret rotation policy

Medium-priority gaps:
- No WAF / reverse-proxy security headers baseline
- No background malware scanning for downloaded attachments
- No signed artifact/dependency verification workflow

## 6. Threat Considerations

### A. Unauthorized data access

Risk:
- anyone with network/API access can read data endpoints.

Mitigations:
- add OAuth2/JWT or SSO
- enforce RBAC by tenant/account/role
- restrict API ingress with VPN/IP allowlist until auth is completed

### B. Credential leakage

Risk:
- `.env` exposure or weak password management.

Mitigations:
- move secrets to secret manager
- rotate DB credentials periodically
- avoid committing `.env` files
- use separate credentials per environment

### C. API abuse / denial of service

Risk:
- expensive search requests can be spammed.

Mitigations:
- reverse-proxy rate limits
- request timeout budgets
- per-client throttling
- caching for common filter lookups

### D. Supply-chain and ingestion risks

Risk:
- downloaded files can be malformed or malicious.

Mitigations:
- run downloads in isolated environment
- enforce extension/type validation
- add optional antivirus scan
- keep parsers/dependencies patched

### E. Data integrity errors

Risk:
- malformed workbook data pollutes production tables.

Mitigations:
- staging table + validation gate before promoting dataset version
- row-level quality checks and anomaly thresholds
- checksums/manifests for reproducibility

## 7. Security Hardening Checklist

### Immediate (before external exposure)

- Add authentication and RBAC.
- Put API behind TLS-terminating reverse proxy.
- Restrict CORS to exact production origins.
- Use non-superuser DB account with minimal privileges.
- Enable DB backups and restore tests.
- Configure access logs with request IDs.

### Next phase

- Add rate limiting.
- Add centralized logging and SIEM integration.
- Add dependency and container image scanning in CI.
- Add vulnerability management and patch cadence.
- Add security incident runbook and owner on-call rotation.

## 8. Secure Configuration Guidance

Environment variables:
- `DATABASE_URL` must use strong password and non-default user.
- `CORS_ORIGINS` must list only trusted frontend domains.
- Keep `.env` out of source control and backups that are broadly accessible.

Network:
- Do not expose PostgreSQL directly to the public internet.
- Allow API ingress only from approved networks/load balancers.

Platform:
- Run API service as non-root user.
- Keep OS and runtime patched.

## 9. Logging and Incident Readiness

Production logging should include:
- timestamp
- request ID
- endpoint
- response status
- latency
- authenticated principal (when auth is implemented)

Minimum incident preparation:
- backup restore verification schedule
- documented escalation path
- post-incident review template

## 10. Compliance and Audit Notes

The system stores public pricing references and lineage metadata, but organizations should still:
- classify data formally
- document retention periods
- maintain change logs for ingestion and schema changes
- retain evidence for dataset source and import date/version
