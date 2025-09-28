# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files, using quotes to handle spaces in the path
COPY "11_ASTS_Console/package.json" "11_ASTS_Console/package-lock.json" ./

# Install dependencies
RUN npm ci

# Copy the rest of the application source code
COPY "11_ASTS_Console/." .

# Build the Next.js application
RUN npm run build

# Stage 2: Production
FROM node:18-alpine

WORKDIR /app

# Copy environment configuration
COPY "11_ASTS_Console/next.config.js" .
COPY "11_ASTS_Console/public" ./public

# Copy build output from the builder stage
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port the app runs on
EXPOSE 3000

# Start the application
CMD ["npm", "start"]