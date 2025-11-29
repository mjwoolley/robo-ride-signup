FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY .env.example ./.env.example

# Create logs directory
RUN mkdir -p logs/screenshots

# Set environment variables for Cloud Run
ENV HOME=/root
ENV TMPDIR=/tmp

# Run the agent once (Cloud Scheduler will trigger hourly)
CMD ["python", "-m", "src.main"]
