FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5004
CMD ["gunicorn", "main:app", "--bind", "0.0.0.0:5004", "--workers", "1", "--threads", "2", "--timeout", "90"]