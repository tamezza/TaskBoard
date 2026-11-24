# Stage 1: build the static files with Node
FROM node:26-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: serve them with nginx. Node is not in the final image.
FROM nginxinc/nginx-unprivileged:stable-alpine
# The nginx image turns every file in /etc/nginx/templates into a
# configuration file at start-up, filling in environment variables.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
ENV API_URL=http://api:8000
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
