# Stage 1: Builder
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files, using quotes to handle spaces in the path
COPY "11ASTSConsole/package.json" "11ASTSConsole/package-lock.json" ./

# Install dependencies
RUN npm ci

# Copy the rest of the application source code
COPY "11ASTSConsole/." .

# Build the Vite application
RUN npm run build

# Stage 2: Production
FROM node:18-alpine

WORKDIR /app

# Copy environment configuration (no Next.js config needed for Vite)
COPY "11ASTSConsole/public" ./public

# Copy build output from the builder stage (Vite builds to dist/)
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

# Expose the port the app runs on (Vite preview default port)
EXPOSE 4173

# Start the application with preview (Vite production server)
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "4173"]