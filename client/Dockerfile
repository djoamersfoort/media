FROM node:20 AS builder
ARG oauth_server
ARG client_id
ARG api_base
ARG redirect_url

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
ENV VITE_OAUTH_SERVER=$oauth_server
ENV VITE_CLIENT_ID=$client_id
ENV VITE_API_BASE=$api_base
ENV VITE_REDIRECT_URL=$redirect_url
RUN npm run build

FROM nginx:stable-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
