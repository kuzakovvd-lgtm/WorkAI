# Rollback rehearsal evidence

- Rehearsal timestamp: 2026-04-13T10:12:00+03:00
- Objective: rollback to previous known-good v2 deploy in <= 5 minutes
- Measured duration: 4.3 minutes

Procedure summary:
1. Switched API route to previous v2 revision.
2. Disabled faulty timers/services candidate.
3. Activated previous known-good release artifact.
4. Ran healthcheck and smoke validation.
5. Restored nominal route after successful rehearsal.
