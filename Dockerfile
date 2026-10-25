# Stage 1: Build virtual environment with uv
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

COPY pyproject.toml .
RUN uv pip compile pyproject.toml -o requirements.txt
RUN uv pip install --no-cache-dir --target=/install -r requirements.txt

# Stage 2: Minimal Distroless Runtime
FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app
COPY --from=builder /install /app/site-packages
COPY src/ /app/src/

ENV PYTHONPATH="/app/site-packages:/app"
USER nonroot

EXPOSE 8000
CMD ["src/api/main.py"]
