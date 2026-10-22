FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends iputils-ping \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY diag_service.py .
COPY shard3.txt /app/shard3.txt
ENV DIAG_BIND=0.0.0.0
EXPOSE 9000
CMD ["python", "diag_service.py"]
