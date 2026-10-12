FROM node:26.11.1-bookworm-slim@sha256:86f07bc9c5dce4578cf37e5a418b7bfc7f817cda25cde66e2b66e95ed86c4567 AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run lint && npm run test -- --run && npm run build

FROM caddy:2.11.4-alpine@sha256:6aeddd44c3078b0f9a35206472a11420648a79c184603ef95957d0a20044cb2b
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
RUN chown -R 65532:65532 /config /data
USER 65532:65532
EXPOSE 80
