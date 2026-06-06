FROM python:3.11-slim

WORKDIR /app

# System deps: build tools + Playwright/Chromium runtime libs
RUN apt-get update && apt-get install -y \
    gcc \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    libx11-6 libx11-xcb1 libxcb1 libxext6 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY app/ ./app/
COPY main.py .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Install Playwright + Chromium (adds ~300MB but enables Profi.ru scraping)
RUN pip install --no-cache-dir playwright && playwright install chromium

# Create data directory
RUN mkdir -p data

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]