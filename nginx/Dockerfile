# Stage 1: build Next.js static export
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --quiet
COPY frontend/ .
# NEXT_PUBLIC_API_URL left unset — defaults to '' so relative /api/* URLs are used
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine
COPY --from=builder /app/out /usr/share/nginx/html
COPY nginx/nginx.dev.conf /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/nginx.prod.conf
