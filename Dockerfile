FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/main.py /app/main.py
COPY backend/main.py /app/backend/main.py
COPY backend/schema.sql /app/backend/schema.sql
COPY backend/seed_data.py /app/backend/seed_data.py
COPY backend/products-seed.json /app/backend/products-seed.json
COPY stores-tw.json /app/stores-tw.json
ENV APP_HOST=0.0.0.0
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]
