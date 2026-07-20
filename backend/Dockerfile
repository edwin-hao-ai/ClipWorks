FROM python:3.11-slim
# espeak-ng：无 TTS API 密钥时的确定性本地旁白合成兜底（含中文声 cmn）。
# 装在共享 Dockerfile 里，backend 与 worker 两个服务都能用（实际合成在 worker 跑）。
RUN apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
