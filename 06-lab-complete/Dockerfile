FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 180 --retries 8 --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
RUN groupadd -r agent && useradd -r -g agent -d /app agent
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY agents/ ./agents/
COPY modules/ ./modules/
COPY templates/ ./templates/
COPY static/ ./static/
COPY sample_data/ ./sample_data/
COPY config.py .
RUN mkdir -p uploads outputs data && chown -R agent:agent /app
USER agent
ENV PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLCONFIGDIR=/tmp/matplotlib
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --timeout-graceful-shutdown 30"]
