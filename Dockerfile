FROM python:3.12-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

FROM node:20-bookworm-slim AS web-build
WORKDIR /app
COPY package.json ./
COPY tsconfig.json vite.config.ts tailwind.config.js postcss.config.js index.html ./
COPY src ./src
COPY server.ts ./
RUN npm install && npm run typecheck && npm run build

FROM node:20-bookworm-slim AS web
ENV NODE_ENV=production \
    PORT=3000 \
    SUPERAGENT_API_URL=http://backend:8000
WORKDIR /app
COPY --from=web-build /app/dist ./dist
COPY --from=web-build /app/node_modules ./node_modules
COPY --from=web-build /app/package.json ./package.json
COPY --from=web-build /app/server.ts ./server.ts
EXPOSE 3000
USER node
CMD ["node", "dist/server.cjs"]
