FROM python:3.13-slim

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
