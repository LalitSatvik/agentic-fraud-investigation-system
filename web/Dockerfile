# Multi-stage: build the static bundle, then serve it with nginx.
FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# The api service is reachable as http://api:8000 inside the compose network.
ENV VITE_API_BASE_URL=http://localhost:8000
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
