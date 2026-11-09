import pika

EXCHANGE = "cidade_inteligente"


def conectar():
    """Abre conexão com o RabbitMQ e declara o exchange topic."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters("localhost")
    )
    channel = connection.channel()
    channel.exchange_declare(
        exchange=EXCHANGE,
        exchange_type="topic",
        durable=True
    )
    return connection, channel


def publicar(channel, routing_key, mensagem):
    """Publica uma mensagem no exchange com a routing key informada."""
    channel.basic_publish(
        exchange=EXCHANGE,
        routing_key=routing_key,
        body=str(mensagem)
    )


def criar_consumidor(channel, routing_keys, callback):
    """Cria uma fila exclusiva, liga às routing keys e registra o callback."""
    resultado = channel.queue_declare(queue="", exclusive=True)
    fila = resultado.method.queue

    for rk in routing_keys:
        channel.queue_bind(exchange=EXCHANGE, queue=fila, routing_key=rk)

    channel.basic_consume(
        queue=fila,
        on_message_callback=callback,
        auto_ack=True
    )


def iniciar(channel, nome):
    """Inicia o loop de consumo até o usuário apertar CTRL+C."""
    print(f"[{nome}] Aguardando mensagens... (CTRL+C para sair)")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print(f"\n[{nome}] Encerrado.")
