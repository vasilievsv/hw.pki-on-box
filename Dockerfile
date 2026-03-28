FROM python:3.13-slim

WORKDIR /app

COPY asw/PKI/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY asw/PKI/ .

ENV PKI_TRNG_MODE=software
ENV PKI_STORAGE_PATH=/data/keys
ENV PKI_DB_PATH=/data/pki.db
ENV PKI_CERTS_PATH=/data/certs

VOLUME ["/data"]
EXPOSE 5000

CMD ["python", "serve.py"]
