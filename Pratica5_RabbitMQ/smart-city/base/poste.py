from common import conectar, criar_consumidor, iniciar

estado = {"limite_lux": 100.0}


def tratar(ch, method, properties, body):
    chave = method.routing_key

    try:
        valor = float(body.decode())
    except ValueError:
        print(f"[POSTE] Valor inválido recebido em {chave}: {body.decode()}")
        return

    if chave == "config.luminosidade":
        estado["limite_lux"] = valor
        print(f"[POSTE] Limite de luminosidade definido: {valor} lux")

    elif chave == "sensor.luminosidade":
        print(f"[POSTE] Sensor de luminosidade: {valor} lux")
        if valor < estado["limite_lux"]:
            print(f"[POSTE] 💡 LÂMPADA ATIVADA (abaixo de {estado['limite_lux']} lux)")
        else:
            print("[POSTE] Sem ajuste necessário (luminosidade suficiente).")


connection, channel = conectar()

criar_consumidor(
    channel,
    ["sensor.luminosidade", "config.luminosidade"],
    tratar
)

iniciar(channel, "POSTE")
