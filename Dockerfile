FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DEBUG=false
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DEBUG=false SECRET_KEY=chave-descartavel-usada-somente-na-compilacao-do-css python manage.py collectstatic --noinput \
    && useradd --create-home hotel && chown -R hotel:hotel /app
USER hotel
EXPOSE 8000
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "--threads=8", "config.wsgi:application"]
