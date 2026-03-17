FROM node:22-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json .
RUN npm install --omit=dev

COPY . .

RUN mkdir -p /data

EXPOSE 3002

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD curl -sf http://localhost:3002/health || exit 1

CMD ["node", "server.js"]
