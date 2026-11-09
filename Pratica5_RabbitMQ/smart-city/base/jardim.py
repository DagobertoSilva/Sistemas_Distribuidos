from common import conectar, criar_consumidor, iniciar

# Estado armazenado (limites iniciais padrão, o usuário pode alterar)
estado = {
    "limite_umidade": 40.0,
    "limite_chuva": 50.0,
    "umidade": None,
    "chuva": None,
}


def avaliar():
    """Aplica a regra do jardim com os dados armazenados."""
    if estado["umidade"] is None or estado["chuva"] is None:
        print("[JARDIM] Aguardando leituras dos dois sensores (umidade e chuva)...")
        return

    chovendo = estado["chuva"] >= estado["limite_chuva"]
    solo_seco = estado["umidade"] < estado["limite_umidade"]

    if chovendo and solo_seco:
        print("[JARDIM] 💧 ATIVADO: chuva detectada e solo seco. Liberando chuva ao solo!")
    else:
        print("[JARDIM] Sem ajuste necessário "
              f"(chovendo={chovendo}, solo_seco={solo_seco}).")


def tratar(ch, method, properties, body):
    chave = method.routing_key

    try:
        valor = float(body.decode())
    except ValueError:
        print(f"[JARDIM] Valor inválido recebido em {chave}: {body.decode()}")
        return

    if chave == "config.umidade":
        estado["limite_umidade"] = valor
        print(f"[JARDIM] Limite de umidade definido: {valor}%")
    elif chave == "config.chuva":
        estado["limite_chuva"] = valor
        print(f"[JARDIM] Limite de chuva definido: {valor}")
    elif chave == "sensor.umidade":
        estado["umidade"] = valor
        print(f"[JARDIM] Sensor de umidade: {valor}%")
        avaliar()
    elif chave == "sensor.chuva":
        estado["chuva"] = valor
        print(f"[JARDIM] Sensor de chuva: {valor}")
        avaliar()


connection, channel = conectar()

criar_consumidor(
    channel,
    ["sensor.umidade", "sensor.chuva", "config.umidade", "config.chuva"],
    tratar
)

iniciar(channel, "JARDIM")
