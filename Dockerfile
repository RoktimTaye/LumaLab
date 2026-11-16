FROM node:22-bookworm-slim AS frontend

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.13.7-python3.11-trixie-slim AS backend

WORKDIR /app
COPY backend/ ./backend/
RUN uv sync --locked --no-dev --project backend
COPY --from=frontend /build/frontend/dist ./frontend/dist

WORKDIR /app/backend
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV TEMP_IMAGE_DIR=/tmp/lumalab/images
RUN mkdir -p /tmp/lumalab/images && chown -R 10001:10001 /app /tmp/lumalab
USER 10001:10001

CMD ["sh", "-c", "exec uvicorn app.main:application --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
