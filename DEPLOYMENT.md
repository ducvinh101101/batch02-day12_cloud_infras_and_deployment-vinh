# Deployment Information

## Medical Research Agent - Railway Demo

- Public URL: https://batch02-agent-railway-production.up.railway.app
- Health: https://batch02-agent-railway-production.up.railway.app/health
- Demo API key: configured privately in Railway as `AGENT_API_KEY`
- Mode: `DEMO_MODE=true`, one Railway replica, `REDIS_URL=memory://`

The Railway Free plan resource limit prevented provisioning a Redis service.
Local Docker Compose still uses Redis and three replicas. Configure
`GEMINI_API_KEY` and set `DEMO_MODE=false` to enable full Gemini analysis.

## Status

Local production stack is complete and verified. Railway public deployment still
requires account login, project creation, and a generated public domain.

## Local Verification Results

Verified on June 12, 2026:

- Production-readiness checker: `21/21` passed.
- Image size: approximately `57.5 MB`.
- Three agent replicas healthy behind Nginx.
- Missing API key returns HTTP `401`.
- Rate limit returns HTTP `429` after 10 requests/minute.
- Cost guard returns HTTP `402` when monthly budget is exhausted.
- Conversation history persists in Redis across multiple agent replicas.
- Graceful shutdown completes and emits structured shutdown logs.

## Public URL

`PENDING_RAILWAY_DEPLOYMENT`

## Platform

Railway

## Required Railway Variables

- `ENVIRONMENT=production`
- `AGENT_API_KEY=<strong-secret>`
- `REDIS_URL=${{Redis.REDIS_URL}}`
- `RATE_LIMIT_PER_MINUTE=10`
- `MONTHLY_BUDGET_USD=10`
- `LOG_LEVEL=INFO`

## Verification Commands

```powershell
$url = "https://YOUR-DOMAIN.up.railway.app"
$headers = @{ "X-API-Key" = "YOUR-KEY" }

Invoke-RestMethod "$url/health"
Invoke-RestMethod "$url/ready"
Invoke-RestMethod -Uri "$url/ask" -Method Post -Headers $headers `
  -ContentType "application/json" -Body '{"question":"Hello"}'
```

## Screenshots

- Deployment dashboard: pending
- Service running: pending
- API test results: pending
