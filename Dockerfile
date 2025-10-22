FROM python:3.11-slim

WORKDIR /app
COPY . /app
ENV PYTHONPATH=/app

CMD ["python", "-m", "hoops_edge", "scan", "--help"]
