﻿# Stage 1: Frontend Build
FROM node:20-bookworm AS frontend
WORKDIR /app

# Install build dependencies and update npm
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --no-install-recommends python3 make g++ git && rm -rf /var/lib/apt/lists/*
RUN npm install -g npm@latest

# Copy package files and install dependencies
COPY 08NeuroHub/.npmrc ./
COPY 08NeuroHub/package*.json ./
# Clean npm cache and install dependencies
RUN npm cache clean --force
RUN npm config set registry https://registry.npmjs.org/
RUN npm install --legacy-peer-deps --verbose --network-timeout 100000

# Copy frontend source files
COPY 08NeuroHub/src/ ./src/
COPY 08NeuroHub/public/ ./public/
COPY 08NeuroHub/index.html ./
COPY 08NeuroHub/postcss.config.js ./
COPY 08NeuroHub/tailwind.config.js ./
COPY 08NeuroHub/tsconfig.json ./
COPY 08NeuroHub/vite.config.ts ./

# Build frontend
RUN npm run build

# Stage 2: Backend Build
FROM python:3.11-bookworm AS backend

# Install system dependencies
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    sqlite3 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY 08NeuroHub/requirements.txt ./
RUN pip install --no-cache-dir --default-timeout=100 --retries 3 -r requirements.txt

# Copy backend source files
COPY 08NeuroHub/backend/ ./backend/
COPY 08NeuroHub/api/ ./api/
COPY 08NeuroHub/config/ ./config/

# Install Node.js dependencies for API
COPY 08NeuroHub/package*.json ./
# Install dependencies with --legacy-peer-deps to avoid peer dependency conflicts
RUN npm install --legacy-peer-deps

# Create necessary directories
RUN mkdir -p logs data

# Copy package.json for potential runtime references
COPY 08NeuroHub/package.json ./

# Expose ports (adjust if needed based on your configuration)
EXPOSE 3000 5555 5556

# Start the application
CMD ["npx", "tsx", "api/server.ts"]
