# Producer

import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost")
)

channel = connection.channel()

channel.queue_declare(queue="fila_teste", durable=True)

mensagem = "Olá, RabbitMQ!"

channel.basic_publish(
    exchange="",
    routing_key="fila_teste",
    body=mensagem
)

print(f"Mensagem enviada: {mensagem}")

connection.close()
