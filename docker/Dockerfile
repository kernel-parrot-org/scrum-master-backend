FROM python:3.12-slim

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    google-chrome-stable \
    ffmpeg \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d '.' -f 1) \
    && wget -q "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION}" -O /tmp/chromedriver_version \
    && CHROMEDRIVER_VERSION=$(cat /tmp/chromedriver_version) \
    && wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" -O /tmp/chromedriver.zip \
    && unzip /tmp/chromedriver.zip -d /tmp/ \
    && mv /tmp/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm /tmp/chromedriver.zip /tmp/chromedriver_version

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONPATH="${PYTHONPATH}:/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV DISPLAY=:99

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --no-dev

# Copy project files
COPY .. /app

# Setup entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "scrum_master.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
