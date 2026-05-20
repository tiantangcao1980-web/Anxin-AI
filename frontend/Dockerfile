# Anxin AI 安心智能助手 - 前端 Dockerfile

# 构建阶段：固定 node minor（升级前同步 .nvmrc / CI）
FROM node:20.18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --legacy-peer-deps

COPY . .
RUN npm run build

# 运行阶段：固定 nginx minor + alpine
FROM nginx:1.27.3-alpine

# [SEC] 移除 nginx 默认服务配置（防止泄露默认 server block）
RUN rm -f /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# [SEC] 非 root 运行（nginx:alpine 已自带 nginx 用户，仅需 chown）
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chmod -R g+w /var/cache/nginx /var/log/nginx
USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --spider --tries=1 http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
