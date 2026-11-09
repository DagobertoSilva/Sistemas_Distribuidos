import pika

connection = pika.BlockingConnection(
    pika.ConnectionParameters("localhost")
)

channel = connection.channel()

channel.queue_declare(queue="fila_teste", durable=True)

def receber_mensagem(ch, method, properties, body):
    print(f"Mensagem recebida: {body.decode()}")

channel.basic_consume(
    queue="fila_teste",
    on_message_callback=receber_mensagem,
    auto_ack=True
)

print("Aguardando mensagens...")

channel.start_consuming()