# Medical Research AI Agent - Production Demo

`AgentMedicalResearch` integrated with the Day 12 production requirements:

- Medical CSV upload, schema detection, AI analysis, chart generation, and web UI.
- API-key authentication, Redis rate limit, monthly cost guard.
- Health/readiness checks, graceful shutdown, Docker, Nginx load balancing.
- Demo mode works without Gemini; full mode uses `GEMINI_API_KEY`.

link demo: https://batch02-agent-railway-production.up.railway.app

## Local Demo

```powershell
cd 06-lab-complete
docker compose up --build --scale agent=3 -d --wait
docker compose ps
```

Open [http://localhost:8000](http://localhost:8000). The local API key is:

```text
dev-key-change-me
```

Upload the included sample:

```text
sample_data/clinical_trial_diabetes.csv
```

Demo mode parses the dataset and shows the complete UI without making an LLM
request. To enable real AI analysis:

```powershell
$env:GEMINI_API_KEY = "your-key"
$env:DEMO_MODE = "false"
docker compose up --build --scale agent=3 -d --wait
```

Reset rate limits and budget before a presentation:

```powershell
docker compose exec redis redis-cli FLUSHDB
```

Stop the stack:

```powershell
docker compose down
```

Use `docker compose down -v` only when uploaded files, charts, sessions, and
Redis data should also be deleted.

## API Tests

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready

$headers = @{ "X-API-Key" = "dev-key-change-me" }
Invoke-RestMethod http://localhost:8000/api/budget -Headers $headers
```

Requests to `/api/chat` and `/api/upload` without `X-API-Key` return HTTP `401`.

## Railway Deployment

1. Create a Railway project.
2. Add a Redis service.
3. Add a GitHub service with root directory `06-lab-complete`.
4. Set these variables on the application service:

```text
ENVIRONMENT=production
AGENT_API_KEY=<strong-random-key>
GEMINI_API_KEY=<your-gemini-key>
GEMINI_MODEL=gemini-2.5-flash
DEMO_MODE=false
REDIS_URL=${{Redis.REDIS_URL}}
RATE_LIMIT_PER_MINUTE=30
MONTHLY_BUDGET_USD=10.0
```

For a Railway test without Gemini, omit `GEMINI_API_KEY` and set
`DEMO_MODE=true`. If the Free plan cannot provision Redis, set
`REDIS_URL=memory://`; this is suitable only for a one-replica demo and loses
rate/budget data on restart.

Generate a public domain and configure health check path `/health`. Enter the
same `AGENT_API_KEY` in the UI sidebar before using protected functions.

Railway runs one application replica by default. Uploaded files, charts, and
SQLite medical session metadata are ephemeral unless a Railway volume is
mounted at `/app/data`, `/app/uploads`, and `/app/outputs`.

## GitHub CI/CD

CI validates Python/JavaScript syntax, production readiness, Compose files, and
the production Docker image. CD deploys this directory to Railway only after CI
passes on `main`.

Configure these GitHub repository secrets:

```text
RAILWAY_TOKEN
RAILWAY_PROJECT_ID
RAILWAY_SERVICE_ID
```
