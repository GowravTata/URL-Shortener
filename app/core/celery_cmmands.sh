# Celery Commands
# Run each command in a separate terminal

# Start the worker
celery -A app.core.celery_app.celery_app worker --loglevel=info

# To Start the beat scheduler
celery -A app.core.celery_app.celery_app beat --loglevel=info

# Flower Console
celery -A app.core.celery_app.celery_app flower --port=5555