# Cliente gRPC - Calculadora (soma, subtração, multiplicação e divisão de três números)

import grpc

import calculadora_pb2
import calculadora_pb2_grpc

MENU = """
========== CALCULADORA gRPC ==========
1 - Soma            (a + b + c)
2 - Subtração       (a - b - c)
3 - Multiplicação   (a * b * c)
4 - Divisão         (a / b / c)
0 - Sair
======================================"""


def ler_numero(rotulo):
    while True:
        try:
            return float(input(f"Digite o {rotulo} número: ").replace(",", "."))
        except ValueError:
            print("Valor inválido. Digite um número (ex.: 3 ou 2.5).")


with grpc.insecure_channel("localhost:50051") as canal:
    cliente = calculadora_pb2_grpc.CalculadoraStub(canal)

    operacoes = {
        "1": ("Soma", cliente.Somar),
        "2": ("Subtração", cliente.Subtrair),
        "3": ("Multiplicação", cliente.Multiplicar),
        "4": ("Divisão", cliente.Dividir),
    }

    while True:
        print(MENU)
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "0":
            print("Encerrando o cliente. Até logo!")
            break

        if opcao not in operacoes:
            print("Opção inválida.")
            continue

        nome, metodo = operacoes[opcao]

        numero1 = ler_numero("primeiro")
        numero2 = ler_numero("segundo")
        numero3 = ler_numero("terceiro")

        requisicao = calculadora_pb2.OperacaoRequest(
            numero1=numero1,
            numero2=numero2,
            numero3=numero3
        )

        try:
            resposta = metodo(requisicao)
            print(f"\n>>> {nome}: resultado = {resposta.resultado}")
        except grpc.RpcError as erro:
            # Ex.: INVALID_ARGUMENT (divisão por zero) ou UNAVAILABLE (servidor offline)
            print(f"\n>>> Erro [{erro.code().name}]: {erro.details()}")
