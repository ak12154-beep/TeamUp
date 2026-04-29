FROM node:20-alpine AS build

WORKDIR /src

COPY . .

ARG VITE_API_URL=/api
ARG VITE_ENABLE_DEMO=false
ARG BACKEND_ORIGIN=http://backend:8000
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ENABLE_DEMO=$VITE_ENABLE_DEMO

RUN set -eux; \
    APP_DIR="."; \
    if [ ! -f package-lock.json ]; then \
    if [ -f frontend/package-lock.json ]; then \
    APP_DIR="frontend"; \
    else \
    echo "Could not find package-lock.json in either ./ or ./frontend." >&2; \
    exit 1; \
    fi; \
    fi; \
    cd "$APP_DIR"; \
    npm ci; \
    chmod +x node_modules/.bin/vite node_modules/vite/bin/vite.js 2>/dev/null || true; \
    npm run build; \
    sed "s|__BACKEND_ORIGIN__|$BACKEND_ORIGIN|g" nginx.conf > /tmp/default.conf; \
    cp -R dist /tmp/dist

FROM nginx:1.27-alpine
COPY --from=build /tmp/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /tmp/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
