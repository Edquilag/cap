# Security Documentation

## 1. Security Scope

This document covers the security posture of the current ZonalHub implementation and the hardening requirements for production.

Current state:
- internal/trusted-network MVP
- no auth/RBAC yet
- read-heavy analytics and export endpoints exposed

## 2. Assets to Protect

Primary assets:
- zonal value data integrity (`zonal_values`)
- data lineage metadata (`source_file`, `source_sheet`, `source_row`, `dataset_version`)
- database credentials and environment secrets
- service availability and query responsiveness

Secondary assets:
- downloaded BIR source files
- ingestion manifests and operational logs

## 3. Trust Boundaries

- browser <-> API
- API <-> database
- ingestion scripts <-> external BIR endpoints
- local/CI/CD <-> deployment infrastructure

## 4. Current Security Controls

- SQLAlchemy parameterized queries (reduces injection risk)
- FastAPI type validation for query parameters
- environment-based configuration (`.env`)
- configurable CORS allowlist
- row-level source lineage retained for traceability
- export safety cap (`export_max_rows`) to reduce abuse blast radius

## 5. Current Gaps

High-priority:
- no authentication
- no authorization/role model
- no rate limiting
- no request identity/correlation middleware
- no audit logs for sensitive reads and export events

Medium-priority:
- no reverse-proxy security header policy baseline
- no malware scan for downloaded workbook attachments
- no centralized secret-management integration

## 6. Threat Considerations

### A. Unauthorized data access

Risk:
- any network client can access API and export endpoints.

Mitigations:
- add SSO/JWT auth
- add RBAC (admin, analyst, partner)
- isolate API ingress with VPN/IP allowlist until auth is complete

### B. API abuse / DoS

Risk:
- expensive search + export calls may be spammed.

Mitigations:
- reverse-proxy rate limiting
- endpoint timeout budgets
- per-client quotas
- monitored alerting on high-volume export usage

### C. Credential leakage

Risk:
- `.env` exposure or weak DB credentials.

Mitigations:
- store secrets in managed secret vault
- rotate DB credentials
- enforce environment-specific credentials
- keep `.env` excluded from VCS

### D. Data integrity risks

Risk:
- malformed workbook content pollutes production dataset.

Mitigations:
- staged ingestion + validation gate
- checksum/manifest tracking
- dataset-version promotion workflow

## 7. Export Endpoint Security Notes

`GET /api/v1/zonal-values/export` considerations:
- currently synchronous and unauthenticated (same as other endpoints)
- returns full source metadata for auditability
- row cap limit prevents unbounded extraction in one request

Recommended controls before internet exposure:
- auth + role checks
- export audit logs (who/when/filters/row-count)
- throttling and burst limits
- optional async export job with signed temporary download URLs

## 8. Secure Configuration Guidance

Environment:
- keep `DATABASE_URL` secret and environment-specific
- restrict `cors_origins` to trusted frontends only
- tune `export_max_rows` based on infrastructure capacity

Database:
- use non-superuser account for app access
- block public DB exposure
- enforce least-privilege network policies

Runtime:
- run app process as non-root user
- patch OS/runtime dependencies regularly

## 9. Logging and Incident Readiness

Production logging should include:
- timestamp
- request ID
- endpoint
- status code
- latency
- authenticated user identity (after auth implementation)
- export truncation flags and requested format

Incident readiness minimum:
- tested backup/restore schedule
- clear escalation path
- post-incident review template

## 10. Hardening Checklist

Immediate:
- implement auth + RBAC
- enforce TLS at ingress
- apply rate limits
- add structured logging + request IDs
- add export audit and anomaly alerts

Next phase:
- SIEM integration
- dependency/container scanning in CI
- incident response playbooks and ownership model
