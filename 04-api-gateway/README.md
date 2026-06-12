# Section 4 - API Gateway and Security

## Develop: API-Key Authentication

```powershell
cd 04-api-gateway\develop
docker build -t api-gateway-develop .
docker run --name api-gateway-develop -d -p 8000:8000 `
  -e AGENT_API_KEY=my-secret-key api-gateway-develop

$env:AGENT_API_KEY = "my-secret-key"
python test_auth.py
docker rm -f api-gateway-develop
```

Expected:

```text
PASS: missing=401, invalid=401, valid=200
```

## Production: JWT, Roles, Rate Limit, Cost Guard

```powershell
cd 04-api-gateway\production
docker build -t api-gateway-production .
docker run --name api-gateway-production -d -p 8000:8000 `
  -e JWT_SECRET=change-this-secret api-gateway-production

python test_advanced.py
docker rm -f api-gateway-production
```

Expected:

```text
PASS: JWT auth, protected endpoint, and admin role
```

Test rate limiting with a fresh container:

```powershell
docker run --name api-gateway-production -d -p 8000:8000 `
  -e JWT_SECRET=change-this-secret api-gateway-production
python test_advanced.py --test rate-limit
docker rm -f api-gateway-production
```

The student account allows 10 requests/minute; request 11 returns HTTP `429`.

## Protection Flow

```text
Request
  -> Authentication (401)
  -> Role authorization (403)
  -> Rate limit (429)
  -> Input validation (422)
  -> Cost guard (402/503)
  -> Agent response (200)
```
