import sys
from common import conectar, criar_consumidor, iniciar

if len(sys.argv) != 2:
    print("Uso: python semaforo.py <id>   (ex.: python semaforo.py 1)")
    sys.exit(1)

meu_id = sys.argv[1].strip().upper()


def tratar(ch, method, properties, body):
    comando = body.decode().strip().upper()

    if comando == "FIM":
        print(f"[SEMÁFORO {meu_id}] ✅ Emergência encerrada. Voltando à operação NORMAL.")
    elif comando == meu_id:
        print(f"[SEMÁFORO {meu_id}] 🟢 VERDE — veículo de urgência avançando!")
    else:
        print(f"[SEMÁFORO {meu_id}] 🔴 VERMELHO — aguardando veículo de urgência "
              f"(prioridade no semáforo {comando}).")


connection, channel = conectar()

criar_consumidor(channel, ["emergencia.semaforo"], tratar)

iniciar(channel, f"SEMÁFORO {meu_id}")
