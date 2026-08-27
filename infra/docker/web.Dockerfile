FROM node:22-slim

RUN corepack enable

WORKDIR /app

COPY apps/web/package.json ./
RUN pnpm install

COPY apps/web/ ./

EXPOSE 3000

CMD ["pnpm", "dev"]
