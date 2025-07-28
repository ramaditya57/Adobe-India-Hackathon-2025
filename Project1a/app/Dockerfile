FROM --platform=linux/amd64 python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /app/deps

FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

COPY --from=builder /app/deps /usr/local/lib/python3.10/site-packages

COPY extractor2.py .
COPY utils.py .

CMD ["python", "extractor2.py"]
