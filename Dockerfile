FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Browsers are already installed by base image, but we still need Node.js for @playwright/mcp
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright MCP server globally
RUN npm install -g @playwright/mcp

# Copy application code
COPY src/ ./src/
COPY .env.example ./.env.example

# Create logs directory
RUN mkdir -p logs/screenshots

# Set environment variables for Cloud Run
ENV HOME=/root
ENV TMPDIR=/tmp
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# CRITICAL: Pass Chromium flags for Cloud Run
# Note: This env var must be read by our Python code and passed to Playwright MCP
ENV CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu --disable-setuid-sandbox"

# Run the agent once (Cloud Scheduler will trigger hourly)
CMD ["python", "-m", "src.main"]
