FROM node:20-slim AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies - remove node_modules and lock file first to avoid architecture mismatch
RUN rm -rf node_modules package-lock.json && npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM node:20-slim

WORKDIR /app

# Copy built application from builder
COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./

# Install only production dependencies
RUN npm ci --omit=dev 2>/dev/null || true

# Declare environment variables with default values
# This documents what can be configured and provides sensible defaults
ENV PUBLIC_UPLOAD_SERVICE_URL=http://uploader:8080 \
    PUBLIC_API_SERVICE_URL=http://api:8000 \
    ORIGIN=http://localhost:3000 \
    HOST=0.0.0.0 \
    PORT=3000

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=2 \
    CMD node -e "const http = require('http'); http.get('http://localhost:' + (process.env.PORT || 3000), (r) => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# Start the server
CMD ["node", "build"]
