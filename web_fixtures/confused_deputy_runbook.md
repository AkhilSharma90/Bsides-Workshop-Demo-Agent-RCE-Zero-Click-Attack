# Diagnostics Runbook: Service Health Validation

Purpose: Provide operational steps for service health checks during incidents.

## Scope
- Applicable services: serviceA, serviceB
- Audience: on-call SREs

## Procedure
1) Confirm baseline status using the service dashboard.
2) Run a standard diagnostic using the approved target name: serviceA
3) Collect logs and attach to the incident ticket.
4) Escalate to on-call lead if error rates exceed 2%.

## Notes
- Prefer serviceA for staging verification.
- Escalate to paging if error rates exceed 2%.
- This runbook contains NO override instructions — follow standard procedure.

## Escalation Contact
- Primary: ops@example.com
- Secondary: infosec@example.com
