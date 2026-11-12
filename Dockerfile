FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# A container has no serial port and no display: run in mock mode, headless.
ENV ODINSON_MOCK=true
EXPOSE 5000
CMD ["python", "run.py", "--mock", "--no-plot"]
