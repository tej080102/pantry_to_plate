# ─────────────────────────────────────────────────────────
# STAGE 1: "builder"
# A temporary container just for installing Python packages.
# ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Tell Python not to write .pyc files (unnecessary in a container)
# and to print logs immediately without buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy ONLY requirements.txt first.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────
# STAGE 2: "runtime"
# ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Security: never run as root inside a container.
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

WORKDIR /app


COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin


COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Tell Docker this container listens on port 8080
EXPOSE 8080

# Health check: Cloud Run pings this every 30s.
# If it fails 3 times in a row, Cloud Run restarts the container.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"

# The command that starts your app.
# --workers 2 means 2 parallel processes handling requests
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "2"]

