# ── Stage 1: Base (install pnpm + dependencies) ───────────────────
FROM node:20-alpine AS base

WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile


# ── Stage 2: Development ───────────────────────────────────────────
FROM base AS development

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host"]


# ── Stage 3: Build (compile static assets) ─────────────────────────
FROM base AS build

COPY . .

RUN pnpm build


# ── Stage 4: Production (serve via Nginx) ──────────────────────────
FROM nginx:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Entrypoint generates /env.js from VITE_* env vars at container start
COPY env.sh /docker-entrypoint.d/env.sh
RUN chmod +x /docker-entrypoint.d/env.sh

EXPOSE 80

ENTRYPOINT ["/docker-entrypoint.d/env.sh"]
