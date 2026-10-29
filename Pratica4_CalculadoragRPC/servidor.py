# Servidor gRPC - Calculadora (soma, subtração, multiplicação e divisão de três números)

from concurrent import futures
import grpc

import calculadora_pb2
import calculadora_pb2_grpc


class CalculadoraServicer(
    calculadora_pb2_grpc.CalculadoraServicer
):
    def Somar(self, request, context):
        resultado = request.numero1 + request.numero2 + request.numero3
        print(f"[Somar] {request.numero1} + {request.numero2} + {request.numero3} = {resultado}")

        return calculadora_pb2.OperacaoResponse(
            resultado=resultado
        )

    def Subtrair(self, request, context):
        resultado = request.numero1 - request.numero2 - request.numero3
        print(f"[Subtrair] {request.numero1} - {request.numero2} - {request.numero3} = {resultado}")

        return calculadora_pb2.OperacaoResponse(
            resultado=resultado
        )

    def Multiplicar(self, request, context):
        resultado = request.numero1 * request.numero2 * request.numero3
        print(f"[Multiplicar] {request.numero1} * {request.numero2} * {request.numero3} = {resultado}")

        return calculadora_pb2.OperacaoResponse(
            resultado=resultado
        )

    def Dividir(self, request, context):
        # Divisão por zero: devolve erro gRPC para o cliente
        if request.numero2 == 0 or request.numero3 == 0:
            print("[Dividir] Erro: tentativa de divisão por zero")
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "Divisão por zero não é permitida."
            )

        resultado = request.numero1 / request.numero2 / request.numero3
        print(f"[Dividir] {request.numero1} / {request.numero2} / {request.numero3} = {resultado}")

        return calculadora_pb2.OperacaoResponse(
            resultado=resultado
        )


server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=10)
)

calculadora_pb2_grpc.add_CalculadoraServicer_to_server(
    CalculadoraServicer(), server
)

server.add_insecure_port("localhost:50051")
server.start()

print("Servidor gRPC iniciado na porta 50051")

server.wait_for_termination()
