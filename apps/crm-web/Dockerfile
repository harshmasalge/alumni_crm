# Production image for Render: build the Vite SPA, serve it via nginx.
# Push to GitHub -> Render rebuilds this Dockerfile and redeploys.
# Render passes every env var (e.g. VITE_API_URL from render.yaml) as a
# Docker build arg automatically, so no dashboard build-arg setup is needed.
# Local dev still uses `npm run dev` via docker-compose command override.
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm install --no-audit --no-fund

COPY . .

ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- "http://localhost:${PORT:-80}/health" || exit 1

# Render injects $PORT; nginx config listens on 80 by default.
CMD ["sh", "-c", "sed -i \"s/listen 80;/listen ${PORT:-80};/\" /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]