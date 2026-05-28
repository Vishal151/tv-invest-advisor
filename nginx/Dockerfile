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

# Run as non-root — nginx:alpine includes the 'nginx' user
RUN chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx \
    && chown -R nginx:nginx /etc/nginx/conf.d \
    && touch /var/run/nginx.pid \
    && chown -R nginx:nginx /var/run/nginx.pid
USER nginx

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
