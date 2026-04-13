# Path policy alignment evidence

- Canonical path: `/opt/workai`
- Active path during cutover: `/opt/workai`
- Legacy/transitional path usage: not active in production cutover window

Validation notes:
- `deploy/systemd/workai-*.service` use `/opt/workai/scripts/*.py` ExecStart.
- Secrets are read from `/etc/workai/secrets/*.env`.
