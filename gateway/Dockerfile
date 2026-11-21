FROM python:3.12-slim
WORKDIR /srv
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY gateway/app ./app
COPY content ./content
ENV CONTENT_DIR=/srv/content DB_PATH=/tmp/gateway.db
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
