FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached when only code changes
COPY code/API/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code only (the front end is a separate image / GitHub Pages)
COPY code/API/app.py code/API/WA.py code/API/OR.py code/API/ID.py ./

# Run as a non-root user
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3)"

# Bind to 0.0.0.0 so the port is reachable from outside the container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "app:app"]
