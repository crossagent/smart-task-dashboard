# --- Frontend Build Stage ---
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm config set registry https://registry.npmmirror.com && npm install
COPY frontend/ ./
RUN npm run build

# --- Backend Stage ---
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple

# Copy backend project files
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy built frontend
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy backend code
COPY . .

# Expose port
EXPOSE 8080
ENV PORT=8080

# Start the dashboard server
CMD ["uv", "run", "python", "-m", "api.server"]
