from common import conectar, publicar

MENU = """
=== PAINEL DO USUÁRIO ===
 1 - Definir limite de UMIDADE do solo (%)
 2 - Definir limite de CHUVA
 3 - Definir limite de LUMINOSIDADE (lux)
 4 - LIGAR limpador das ruas
 5 - DESLIGAR limpador das ruas
 6 - Emergência: dar passagem a um semáforo
 7 - Encerrar emergência (voltar ao normal)
 0 - Sair
"""

connection, channel = conectar()


def ler_numero(texto):
    try:
        return float(input(texto).strip())
    except ValueError:
        print("Digite um número válido.")
        return None


try:
    while True:
        print(MENU)
        opcao = input("Opção: ").strip()

        if opcao == "0":
            break

        elif opcao == "1":
            v = ler_numero("Limite de umidade (%): ")
            if v is not None:
                publicar(channel, "config.umidade", v)
                print(f"⚙️ Limite de umidade enviado: {v}")

        elif opcao == "2":
            v = ler_numero("Limite de chuva: ")
            if v is not None:
                publicar(channel, "config.chuva", v)
                print(f"⚙️ Limite de chuva enviado: {v}")

        elif opcao == "3":
            v = ler_numero("Limite de luminosidade (lux): ")
            if v is not None:
                publicar(channel, "config.luminosidade", v)
                print(f"⚙️ Limite de luminosidade enviado: {v}")

        elif opcao == "4":
            publicar(channel, "comando.limpador", "LIGA")
            print("▶️ Comando LIGA enviado ao limpador.")

        elif opcao == "5":
            publicar(channel, "comando.limpador", "DESLIGA")
            print("⏹️ Comando DESLIGA enviado ao limpador.")

        elif opcao == "6":
            sem_id = input("Id do semáforo que deve avançar (ex.: 1): ").strip()
            if sem_id:
                publicar(channel, "emergencia.semaforo", sem_id)
                print(f"🚑 Emergência enviada: semáforo {sem_id} liberado, demais em vermelho.")

        elif opcao == "7":
            publicar(channel, "emergencia.semaforo", "FIM")
            print("✅ Fim da emergência enviado.")

        else:
            print("Opção inválida.")
finally:
    connection.close()
    print("Painel encerrado.")
