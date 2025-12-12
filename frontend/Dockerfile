# Multi-stage build for React + Vite frontend

# Stage 1: Build the application
FROM node:20-alpine AS builder

# Build arguments for API URLs
ARG VITE_AUTH_SERVICE_URL
ARG VITE_BOOK_SERVICE_URL
ARG VITE_TRANSLATION_SERVICE_URL
ARG VITE_USER_SERVICE_URL

# Set them as environment variables for the build
ENV VITE_AUTH_SERVICE_URL=$VITE_AUTH_SERVICE_URL
ENV VITE_BOOK_SERVICE_URL=$VITE_BOOK_SERVICE_URL
ENV VITE_TRANSLATION_SERVICE_URL=$VITE_TRANSLATION_SERVICE_URL
ENV VITE_USER_SERVICE_URL=$VITE_USER_SERVICE_URL

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application (env vars will be embedded by Vite)
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

