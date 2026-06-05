FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
# Run migrations then serve. For real deploys, run migrate as a separate release step.
CMD sh -c "python manage.py migrate --noinput && \
    gunicorn smartfinance.wsgi:application --bind 0.0.0.0:8000 --workers 3"
