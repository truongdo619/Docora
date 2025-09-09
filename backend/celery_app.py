from celery import Celery

app = Celery(
    "tasks",
    broker="redis://localhost:6377/0",  # Replace with your Redis URL
    backend="redis://localhost:6377/0"
)

# app = Celery(
#     "dev_tasks",
#     broker="amqp://admin:admin@localhost:5672/dev_tasks",  # Replace with your Redis URL
#     backend="amqp"
# )
