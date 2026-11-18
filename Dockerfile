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
RUN mkdir -p /tmp/lumalab/images && chmod 700 /tmp/lumalab/images && chown 10001:10001 /tmp/lumalab/images && chown -R 10001:10001 /app
USER 10001:10001

CMD ["python", "-m", "app.deploy"]
