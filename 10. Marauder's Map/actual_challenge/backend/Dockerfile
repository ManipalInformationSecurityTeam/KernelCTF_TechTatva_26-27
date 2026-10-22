# Stage 1: build the React/Vite frontend with its own toolchain.
FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY marauders-map/package.json marauders-map/package-lock.json ./
RUN npm ci
COPY marauders-map/ .
RUN npm run build

# Stage 2: the Flask backend, serving the built frontend as static files.
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY --from=frontend-build /frontend/dist ./dist

RUN python seed.py

EXPOSE 5000

CMD ["python", "app.py"]
