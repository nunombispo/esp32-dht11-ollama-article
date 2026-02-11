FROM python:3.13-slim

# Note: On Linux, you may need to run the container with --add-host=host.docker.internal:host-gateway
# to allow the container to access services running on the host machine

WORKDIR /app

# Copy requirements and install dependencies
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY gateway/main.py .

# Expose port (Dokku will set PORT env var)
EXPOSE 5000

# Run the application
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-5000}
