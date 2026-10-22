FROM python:3.12-slim
WORKDIR /app
COPY app.py .
ENV DIAG_URL=http://diag:9000/ping
ENV GALLERY_BIND=0.0.0.0
EXPOSE 8080
CMD ["python", "app.py"]
