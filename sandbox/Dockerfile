# Multi-stage Dockerfile for the sandbox.
# Stage 1 builds the React/Vite/Tailwind frontend.
# Stage 2 serves it via FastAPI, with the ranker mounted in.

# ----- Stage 1: build frontend -----
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY sandbox/frontend/package.json sandbox/frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY sandbox/frontend/ ./
RUN npm run build

# ----- Stage 2: Python runtime -----
FROM python:3.11-slim AS runtime
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
COPY sandbox/backend/requirements.txt ./sandbox-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r sandbox-requirements.txt

# Copy source
COPY src/ ./src/
COPY sandbox/backend/ ./sandbox/backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./sandbox/frontend/dist

# Expose port
EXPOSE 7860

# HF Spaces convention is port 7860; bind to 0.0.0.0
CMD ["uvicorn", "sandbox.backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
