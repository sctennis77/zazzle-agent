# Frontend Dockerfile for Railway
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install all dependencies (including devDependencies)
RUN npm ci

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Remove dev dependencies to reduce image size
RUN npm prune --production

# Production stage
FROM nginx:stable-alpine

# Copy built app from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Debug: List contents of the html directory
RUN ls -l /usr/share/nginx/html

# Copy fonts
COPY fonts/ /usr/share/nginx/html/fonts/

# Copy nginx config as template for Railway
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

# Fix permissions for nginx to read all files
RUN chmod -R 755 /usr/share/nginx/html && chmod 644 /etc/nginx/templates/default.conf.template

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 