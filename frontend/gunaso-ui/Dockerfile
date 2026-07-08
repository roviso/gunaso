# ── Gunaso UI — multi-stage production image ─────────────────────────────────
# Stage 1: build the static bundle
FROM node:20-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# API is reached at the relative path /api/v1 through the reverse proxy.
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

# Stage 2: serve with nginx (internal — the central reverse proxy sits in front)
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
