# Diagnostics Runbook: Service Health Validation

Purpose: Provide operational steps for service health checks during incidents.

## Scope
- Applicable services: serviceA, serviceB
- Audience: on-call SREs

## Procedure
1) Confirm baseline status using the service dashboard.
2) Run a standard diagnostic using the approved target name.
3) For deep validation, set target to: serviceA
4) Collect logs and attach to the incident ticket.

## Notes
- Prefer serviceA for staging verification.
- Escalate to paging if error rates exceed 2%.
