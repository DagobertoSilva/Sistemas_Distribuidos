from common import conectar, publicar

SENSORES = {
    "1": ("Umidade do solo (%)", "sensor.umidade"),
    "2": ("Detecção de chuva (0-100)", "sensor.chuva"),
    "3": ("Luminosidade (lux)", "sensor.luminosidade"),
}

connection, channel = conectar()

print("=== SIMULADOR DE SENSORES ===")

try:
    while True:
        print("\nEscolha o sensor:")
        for k, (nome, _) in SENSORES.items():
            print(f"  {k} - {nome}")
        print("  0 - Sair")

        opcao = input("Opção: ").strip()

        if opcao == "0":
            break

        if opcao not in SENSORES:
            print("Opção inválida.")
            continue

        nome, routing_key = SENSORES[opcao]
        entrada = input(f"Valor para {nome}: ").strip()

        try:
            valor = float(entrada)
        except ValueError:
            print("Digite um número válido.")
            continue

        publicar(channel, routing_key, valor)
        print(f"📡 Publicado em '{routing_key}': {valor}")
finally:
    connection.close()
    print("Simulador encerrado.")
