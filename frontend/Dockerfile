ARG NODE_BASE_IMAGE=node:22-alpine
ARG NGINX_BASE_IMAGE=nginx:1.27-alpine

FROM ${NODE_BASE_IMAGE} AS build

ARG NPM_REGISTRY=https://registry.npmjs.org

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm config set registry "$NPM_REGISTRY" \
    && npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 10000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm ci

COPY frontend/ .
RUN npm run build

FROM ${NGINX_BASE_IMAGE} AS runtime

COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --retries=5 \
    CMD wget -q -O /dev/null http://127.0.0.1/health || exit 1
