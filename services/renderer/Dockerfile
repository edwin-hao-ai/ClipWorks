FROM node:22-bookworm

ARG APT_MIRROR=
ARG NPM_REGISTRY=
RUN if [ -n "$APT_MIRROR" ]; then \
      if [ -f /etc/apt/sources.list ]; then sed -i "s|http://deb.debian.org/debian|$APT_MIRROR|g" /etc/apt/sources.list; fi && \
      if [ -f /etc/apt/sources.list.d/debian.sources ]; then sed -i "s|http://deb.debian.org/debian|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources; fi; \
    fi && \
    apt-get update && apt-get install -y -o Acquire::Retries=3 \
    ffmpeg \
    python3 \
    python3-pip \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && \
    npm install

COPY requirements.txt ./
ARG PIP_INDEX_URL=
RUN python3 -m venv /app/.venv && \
    if [ -n "$PIP_INDEX_URL" ]; then /app/.venv/bin/pip config set global.index-url "$PIP_INDEX_URL"; fi && \
    /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

RUN /app/.venv/bin/python -m playwright install chromium

COPY remotion ./remotion
RUN if [ -n "$NPM_REGISTRY" ]; then npm config set registry "$NPM_REGISTRY"; fi && \
    cd remotion && npm install

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV REMOTION_DISABLE_CHROMIUM_SANDBOX=true

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
