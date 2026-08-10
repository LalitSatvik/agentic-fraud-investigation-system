# deploy/

Docker Compose reference deployment: Postgres, a one-off seed step that loads the committed
dataset, the API, and the reviewer dashboard.

```bash
ANTHROPIC_API_KEY=sk-... docker compose -f deploy/docker-compose.yml up --build
```

Unlike local development, this doesn't split the API and agent across two Python
environments — `Dockerfile` builds a single Python 3.11 image that runs both, since the
version constraint that motivates the split locally (see `../docs/DEVELOPMENT.md`) doesn't
apply to a fresh container.

Not yet exercised end-to-end in CI — validate locally before relying on it.
