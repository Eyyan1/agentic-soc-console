web: python manage.py migrate && gunicorn ASP.asgi:application -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --workers 1 --timeout 60
