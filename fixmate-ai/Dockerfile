# One small runtime image is reused by the separate Compose services.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FIXMATE_DATABASE_PATH=/app/data/fixmate.db \
    FIXMATE_LLM_PROVIDER=disabled

WORKDIR /app

# Install Python dependencies before source code to improve build caching.
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.txt

# The application needs write access only to its local SQLite volume.
RUN groupadd --system fixmate && \
    useradd --system --gid fixmate --home-dir /app --shell /usr/sbin/nologin fixmate && \
    mkdir -p /app/data && \
    chown -R fixmate:fixmate /app

COPY --chown=fixmate:fixmate . .

USER fixmate

EXPOSE 8501 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"]

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
