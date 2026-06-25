# ====== 前端 Dockerfile（构建 + nginx 托管） ======
# 阶段 1：构建
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY package*.json ./
# 使用淘宝 npm 镜像加速（国内服务器）
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY . .
RUN npm run build

# 阶段 2：nginx 托管
FROM nginx:alpine

COPY --from=frontend-builder /build/dist /usr/share/nginx/html
# nginx.conf 通过 docker-compose volumes 挂载，或构建时从 context 拷贝
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
