FROM node:22-bookworm

ARG APT_MIRROR=
ARG NPM_REGISTRY=
RUN if [ -n "$APT_MIRROR" ]; then \
      if [ -f /etc/apt/sources.list ]; then sed -i "s|http://deb.debian.org/debian|$APT_MIRROR|g" /etc/apt/sources.list; fi && \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i "s|http://deb.debian.org/debian|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources; fi; \
    fi && \
    apt-get update && apt-get install -y -o Acquire::Retries=10 --fix-missing \
    ffmpeg \
    python3 \
    python3-pip \
    python3-venv \
    wget \
    ca-certificates \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Install Noto CJK fonts from local files to avoid build-time network dependencies.
COPY fonts/NotoSansCJKsc-Regular.otf fonts/NotoSansCJKsc-Bold.otf /usr/share/fonts/noto/
RUN fc-cache -fv

WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && \
    npm install

COPY requirements.txt ./
ARG PIP_INDEX_URL=
RUN python3 -m venv /app/.venv && \
    if [ -n "$PIP_INDEX_URL" ]; then /app/.venv/bin/pip config set global.index-url "$PIP_INDEX_URL"; fi && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# Install Chromium system dependencies and a single Chromium binary via Playwright.
# Remotion, HyperFrames/Puppeteer, and video-use can all share this Chromium.
RUN /app/.venv/bin/python -m playwright install-deps chromium && \
    /app/.venv/bin/python -m playwright install chromium && \
    PLAYWRIGHT_CHROME=$(find /root/.cache/ms-playwright -path '*/chrome-linux/chrome' -type f | head -n1) && \
    if [ -z "$PLAYWRIGHT_CHROME" ]; then echo "Playwright Chromium not found" && exit 1; fi && \
    ln -sf "$PLAYWRIGHT_CHROME" /usr/local/bin/chrome && \
    echo "Chromium: $PLAYWRIGHT_CHROME"

COPY remotion ./remotion
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && \
    cd remotion && npm install

COPY . .
COPY patch-remotion.py /app/patch-remotion.py
RUN python3 /app/patch-remotion.py

ENV PATH="/app/.venv/bin:$PATH"
ENV REMOTION_DISABLE_CHROMIUM_SANDBOX=true
ENV REMOTION_CHROMIUM_PATH=/usr/local/bin/chrome
ENV CHROME_PATH=/usr/local/bin/chrome
ENV PUPPETEER_EXECUTABLE_PATH=/usr/local/bin/chrome
ENV HYPERFRAMES_BROWSER_PATH=/usr/local/bin/chrome

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
