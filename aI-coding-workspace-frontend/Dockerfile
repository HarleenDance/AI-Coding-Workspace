# ====== 前端 Dockerfile（构建 + nginx 托管） ======
# 阶段 1：构建
FROM node:20-alpine AS frontend-builder

WORKDIR /build
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# 阶段 2：nginx 托管
FROM nginx:alpine

COPY --from=frontend-builder /build/dist /usr/share/nginx/html
COPY ../deploy/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
