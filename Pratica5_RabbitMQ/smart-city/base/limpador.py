from common import conectar, criar_consumidor, iniciar

estado = {"ligado": False}


def tratar(ch, method, properties, body):
    comando = body.decode().strip().upper()

    if comando == "LIGA":
        if estado["ligado"]:
            print("[LIMPADOR] Já está ligado.")
        else:
            estado["ligado"] = True
            print("[LIMPADOR] 🧹 LIGADO: limpando as ruas...")
    elif comando == "DESLIGA":
        if not estado["ligado"]:
            print("[LIMPADOR] Já está desligado.")
        else:
            estado["ligado"] = False
            print("[LIMPADOR] ⏹️ DESLIGADO: limpeza encerrada.")
    else:
        print(f"[LIMPADOR] Comando desconhecido: {comando}")


connection, channel = conectar()

criar_consumidor(channel, ["comando.limpador"], tratar)

iniciar(channel, "LIMPADOR")
