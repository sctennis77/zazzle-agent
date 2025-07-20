# Frontend Dockerfile for Railway - Optimized
FROM node:18-alpine AS dependencies

# Install build essentials for potential native dependencies
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files first for better layer caching
COPY package*.json ./

# Install dependencies with cache optimization
RUN npm ci --only=production --no-audit --no-fund && \
    npm cache clean --force

# Development dependencies stage
FROM node:18-alpine AS dev-dependencies

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies)
RUN npm ci --no-audit --no-fund && \
    npm cache clean --force

# Build stage
FROM node:18-alpine AS builder

# Accept build arguments
ARG VITE_API_BASE_URL
ARG VITE_STRIPE_PUBLISHABLE_KEY
ARG VITE_COMISSION_ART_ENABLED
ARG VITE_REDDIT_MODE

WORKDIR /app

# Copy all dependencies from dev-dependencies stage
COPY --from=dev-dependencies /app/node_modules ./node_modules
COPY package*.json ./

# Copy source code (excluding node_modules via .dockerignore)
COPY . .

# Set VITE_API_BASE_URL as an environment variable for the build
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_STRIPE_PUBLISHABLE_KEY=$VITE_STRIPE_PUBLISHABLE_KEY
ENV VITE_COMISSION_ART_ENABLED=$VITE_COMISSION_ART_ENABLED
ENV VITE_REDDIT_MODE=$VITE_REDDIT_MODE

# Print environment variables for debugging
RUN printenv

# Build the app with optimizations
RUN npm run build && \
    # Remove source maps and unnecessary files from dist
    find /app/dist -name "*.map" -delete && \
    # Clean up node_modules to reduce image size
    rm -rf /app/node_modules

# Production stage
FROM nginx:stable-alpine AS production

# Install curl for health checks
RUN apk add --no-cache curl

# Copy built app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy fonts
COPY fonts/ /usr/share/nginx/html/fonts/

# Copy optimized nginx config as template for Railway
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Set permissions for nginx files
RUN chmod -R 755 /usr/share/nginx/html && \
    chmod 644 /etc/nginx/templates/default.conf.template

# Expose port
EXPOSE 80

# Optimized health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 