# Section 5 - Scaling and Reliability

## Develop: Health, Readiness, Graceful Shutdown

```powershell
cd 05-scaling-reliability\develop
pip install -r requirements.txt
python app.py
```

In another PowerShell terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/ready
Invoke-RestMethod -Method Post "http://localhost:8000/ask?question=hello"
```

Stop with `Ctrl+C` and observe the graceful shutdown logs.

## Production: Stateless Scaling with Redis

```powershell
cd 05-scaling-reliability\production
docker compose up --build --scale agent=3 -d --wait
docker compose ps
docker compose run --rm --no-deps -e BASE_URL=http://nginx agent python test_stateless.py
```

Expected results:

- Redis, Nginx, and three agent replicas are healthy.
- Requests show multiple `served_by` instance IDs.
- Conversation history remains complete across instances.

Test that traffic continues when one replica stops:

```powershell
$agent = docker compose ps -q agent | Select-Object -First 1
docker stop $agent
docker compose run --rm --no-deps -e BASE_URL=http://nginx agent python test_stateless.py
docker start $agent
```

Inspect Redis and logs:

```powershell
docker compose exec redis redis-cli --scan --pattern "session:*"
docker compose logs agent
```

Stop the stack:

```powershell
docker compose down
```

Use `docker compose down -v` only when you also want to delete Redis data.
