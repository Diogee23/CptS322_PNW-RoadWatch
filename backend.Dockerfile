# Use Python 3.13.14
FROM python:3.13.14-slim

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from creating unnecessary cache files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy and install backend dependencies
COPY code/api/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application and state-specific modules
COPY code/api/*.py .

# Default port (Railway or Render can override this)
ENV PORT=8000

# Document the application port
EXPOSE 8000

# Start Flask using Gunicorn
CMD ["sh", "-c", "exec gunicorn app:app --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 60"]
