# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Configure Poetry to not create virtual environment (we're already in a container)
RUN poetry config virtualenvs.create false

# Set work directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Install Python dependencies (without installing the current project)
RUN poetry install --only=main --no-root

# Copy the entire project
COPY . .

# Install the project in development mode
RUN poetry install --only=main

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose the port that LangGraph server runs on
EXPOSE 2024

# Health check to ensure the service is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:2024/health || exit 1

# Default command to run the LangGraph server
CMD ["poetry", "run", "langgraph", "dev", "--host", "0.0.0.0", "--port", "2024"] 