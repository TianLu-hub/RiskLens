FROM node:22-slim AS build

RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm build

FROM node:22-slim AS runtime
RUN corepack enable
WORKDIR /app
COPY --from=build /app ./

EXPOSE 3000
CMD ["pnpm", "start", "--ip", "0.0.0.0", "--port", "3000"]
