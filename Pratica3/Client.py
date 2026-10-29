#!/usr/bin/env python3
# A linha acima (shebang) permite executar o arquivo diretamente no Linux/macOS
# com "./client.py", usando o interpretador python3 do sistema.

"""
Cliente de teste.

Cria N clientes simultâneos (um por thread). Cada um:
  1. gera 1.000.000 de números aleatórios entre 0 e 1000;
  2. conecta no servidor;
  3. espera todos os outros clientes (barreira) para começarem juntos;
  4. envia os números e recebe a soma;
  5. confere a resposta com a soma calculada localmente.
"""

# ---------------------------------------------------------------------------
# IMPORTAÇÕES (todas da biblioteca padrão do Python, nada para instalar)
# ---------------------------------------------------------------------------
import argparse    # lê argumentos da linha de comando (--host, --port, --clients...)
import random      # sorteia os números aleatórios
import socket      # comunicação de rede via TCP
import struct      # converte números em bytes (e vice-versa) com formato fixo
import sys         # ordem dos bytes da máquina e código de saída do programa
import threading   # cria os clientes simultâneos (threads) e a barreira
import time        # relógio de alta precisão para medir os tempos
from array import array  # vetor compacto de números inteiros de tamanho fixo


# ---------------------------------------------------------------------------
# CONSTANTES DO PROTOCOLO DE COMUNICAÇÃO
# (devem ser IGUAIS às do servidor, senão os dois não se entendem)
# ---------------------------------------------------------------------------

# Cabeçalho enviado ao servidor: inteiro sem sinal de 4 bytes com a QUANTIDADE
# de números que virão em seguida.
#   "!" = ordem de bytes de rede (big-endian)
#   "I" = unsigned int (4 bytes)
FORMATO_CABECALHO_QUANTIDADE_NUMEROS = struct.Struct("!I")

# Resposta recebida do servidor: inteiro sem sinal de 8 bytes com a SOMA TOTAL.
#   "Q" = unsigned long long (8 bytes)
FORMATO_RESPOSTA_SOMA_TOTAL = struct.Struct("!Q")


# ---------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: LER UMA QUANTIDADE EXATA DE BYTES DO SOCKET
# ---------------------------------------------------------------------------
def receber_exatamente_n_bytes(conexao_socket_com_o_servidor, quantidade_de_bytes_esperada):
    """Lê exatamente `quantidade_de_bytes_esperada` bytes do socket.

    O TCP é um fluxo contínuo de bytes: uma única chamada de recv pode devolver
    menos bytes do que o pedido (os dados chegam em pedaços). Por isso repetimos
    a leitura até completar a quantidade desejada.
    """
    # Acumula os bytes recebidos até chegar ao total esperado.
    bytes_recebidos_ate_agora = bytearray()

    while len(bytes_recebidos_ate_agora) < quantidade_de_bytes_esperada:
        # Pede apenas o que ainda falta receber.
        pedaco_de_bytes_recebido = conexao_socket_com_o_servidor.recv(
            quantidade_de_bytes_esperada - len(bytes_recebidos_ate_agora)
        )

        # Se recv devolver vazio, o servidor fechou a conexão antes de responder.
        if not pedaco_de_bytes_recebido:
            raise ConnectionError("Conexão encerrada pelo servidor")

        # Junta o pedaço recebido ao que já tínhamos.
        bytes_recebidos_ate_agora.extend(pedaco_de_bytes_recebido)

    # Converte para bytes imutáveis antes de devolver.
    return bytes(bytes_recebidos_ate_agora)


# ---------------------------------------------------------------------------
# FUNÇÃO EXECUTADA POR CADA THREAD: UM CLIENTE COMPLETO
# ---------------------------------------------------------------------------
def executar_um_cliente(identificador_do_cliente,
                        endereco_do_servidor,
                        porta_do_servidor,
                        quantidade_de_numeros_a_enviar,
                        barreira_de_sincronizacao_entre_clientes,
                        resultados_de_todos_os_clientes):
    """Executa UM cliente do início ao fim. Roda em uma thread própria.

    O resultado é gravado em `resultados_de_todos_os_clientes`, um dicionário
    compartilhado em que cada cliente usa a sua própria chave (o identificador),
    por isso não há conflito entre as threads.
    """
    try:
        # -----------------------------------------------------------------
        # ETAPA 1: GERAR OS NÚMEROS E A SOMA ESPERADA (fora da medição)
        # -----------------------------------------------------------------
        # Sorteia `quantidade_de_numeros_a_enviar` inteiros entre 0 e 1000
        # (inclusive) e os guarda em um vetor de inteiros de 2 bytes ("H" = uint16).
        vetor_de_numeros_aleatorios = array(
            "H",
            random.choices(range(0, 1001), k=quantidade_de_numeros_a_enviar),
        )

        # Soma calculada AQUI, localmente, para depois conferir a resposta do
        # servidor. Deve ser feita ANTES do byteswap abaixo (valores corretos).
        soma_esperada_calculada_localmente = sum(vetor_de_numeros_aleatorios)

        # A rede usa big-endian. Se esta máquina usa little-endian (a maioria
        # dos PCs), invertemos os bytes de cada número antes de enviar, para o
        # servidor interpretar os valores corretamente.
        if sys.byteorder == "little":
            vetor_de_numeros_aleatorios.byteswap()

        # Mensagem completa a enviar = cabeçalho (4 bytes com a quantidade)
        # seguido de todos os números convertidos em bytes (2 bytes cada).
        mensagem_completa_a_enviar = (
            FORMATO_CABECALHO_QUANTIDADE_NUMEROS.pack(quantidade_de_numeros_a_enviar)
            + vetor_de_numeros_aleatorios.tobytes()
        )

        # -----------------------------------------------------------------
        # ETAPA 2: CONECTAR NO SERVIDOR
        # -----------------------------------------------------------------
        # Abre a conexão TCP com o servidor.
        socket_conectado_ao_servidor = socket.create_connection(
            (endereco_do_servidor, porta_do_servidor)
        )

        # -----------------------------------------------------------------
        # ETAPA 3: ESPERAR TODOS OS CLIENTES (BARREIRA)
        # -----------------------------------------------------------------
        # Cada thread para aqui até que TODAS as threads cheguem a este ponto.
        # Quando a última chega, todas são liberadas ao mesmo tempo. Assim
        # todos os clientes começam a enviar juntos (simultaneidade real).
        barreira_de_sincronizacao_entre_clientes.wait()

        # -----------------------------------------------------------------
        # ETAPA 4: ENVIAR OS NÚMEROS E RECEBER A SOMA
        # -----------------------------------------------------------------
        # Instante imediatamente antes do envio.
        instante_antes_de_enviar = time.perf_counter()

        # Envia a mensagem inteira (cabeçalho + 1.000.000 de números).
        socket_conectado_ao_servidor.sendall(mensagem_completa_a_enviar)

        # Espera os 8 bytes da resposta e os converte de volta em um inteiro.
        soma_recebida_do_servidor = FORMATO_RESPOSTA_SOMA_TOTAL.unpack(
            receber_exatamente_n_bytes(
                socket_conectado_ao_servidor,
                FORMATO_RESPOSTA_SOMA_TOTAL.size,
            )
        )[0]  # unpack devolve uma tupla; pegamos o primeiro (único) item

        # Instante em que a resposta chegou por completo.
        instante_depois_de_receber_resposta = time.perf_counter()

        # Encerra a conexão com o servidor.
        socket_conectado_ao_servidor.close()

        # -----------------------------------------------------------------
        # ETAPA 5: CONFERIR A RESPOSTA E GUARDAR O RESULTADO
        # -----------------------------------------------------------------
        # True se a soma do servidor for igual à soma calculada localmente.
        servidor_respondeu_corretamente = (
            soma_recebida_do_servidor == soma_esperada_calculada_localmente
        )

        # Tupla com tudo que será exibido no final:
        # (acertou?, tempo de ida e volta em segundos, soma recebida, soma esperada)
        resultados_de_todos_os_clientes[identificador_do_cliente] = (
            servidor_respondeu_corretamente,
            instante_depois_de_receber_resposta - instante_antes_de_enviar,
            soma_recebida_do_servidor,
            soma_esperada_calculada_localmente,
        )

    except Exception as erro_ocorrido:
        # Qualquer falha deste cliente é registrada no terminal.
        print(f"[CLIENTE {identificador_do_cliente}] Erro: {erro_ocorrido}", flush=True)

        # "Quebra" a barreira para liberar os outros clientes que estejam
        # esperando; sem isso eles ficariam parados para sempre aguardando
        # este cliente que falhou.
        barreira_de_sincronizacao_entre_clientes.abort()

        # Registra este cliente como falho (sem tempo e sem somas).
        resultados_de_todos_os_clientes[identificador_do_cliente] = (False, 0.0, None, None)


# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL: LÊ OS ARGUMENTOS, DISPARA OS CLIENTES E MOSTRA O RESUMO
# ---------------------------------------------------------------------------
def main():
    # --- Leitura dos argumentos da linha de comando ---
    leitor_de_argumentos_da_linha_de_comando = argparse.ArgumentParser(
        description="Cliente de soma"
    )
    # Endereço do servidor. "127.0.0.1" = esta própria máquina.
    leitor_de_argumentos_da_linha_de_comando.add_argument("--host", default="127.0.0.1")
    # Porta TCP do servidor (deve ser a mesma usada no server.py).
    leitor_de_argumentos_da_linha_de_comando.add_argument("--port", type=int, default=5000)
    # Quantos clientes simultâneos serão criados (1, 4, 8 ou 16 na prática).
    leitor_de_argumentos_da_linha_de_comando.add_argument(
        "--clients", type=int, default=1, help="clientes simultâneos"
    )
    # Quantos números cada cliente envia (1.000.000 conforme o enunciado).
    leitor_de_argumentos_da_linha_de_comando.add_argument(
        "--numbers", type=int, default=1_000_000
    )
    argumentos_recebidos = leitor_de_argumentos_da_linha_de_comando.parse_args()

    print(
        f"[CLIENTE] Iniciando {argumentos_recebidos.clients} cliente(s) simultâneo(s)...",
        flush=True,
    )

    # Barreira para N participantes: só libera quando N threads chamarem wait().
    barreira_de_sincronizacao_entre_clientes = threading.Barrier(argumentos_recebidos.clients) # -------------------------------------------------------------------------

    # Dicionário compartilhado: chave = identificador do cliente (0, 1, 2...),
    # valor = tupla com o resultado daquele cliente.
    resultados_de_todos_os_clientes = {}

    # Cria uma thread para cada cliente (ainda não as inicia).
    lista_de_threads_dos_clientes = [
        threading.Thread(
            target=executar_um_cliente,
            args=(
                identificador_do_cliente,
                argumentos_recebidos.host,
                argumentos_recebidos.port,
                argumentos_recebidos.numbers,
                barreira_de_sincronizacao_entre_clientes,
                resultados_de_todos_os_clientes,
            ),
        )
        for identificador_do_cliente in range(argumentos_recebidos.clients)
    ]

    # Inicia todas as threads (cada uma começa a gerar seus números).
    for thread_de_um_cliente in lista_de_threads_dos_clientes:
        thread_de_um_cliente.start()

    # Espera todas as threads terminarem antes de mostrar o resumo.
    for thread_de_um_cliente in lista_de_threads_dos_clientes:
        thread_de_um_cliente.join()

    # --- Exibição do resumo de cada cliente ---
    todos_os_clientes_receberam_soma_correta = True

    # Percorre os resultados em ordem crescente de identificador.
    for identificador_do_cliente in sorted(resultados_de_todos_os_clientes):
        (
            servidor_respondeu_corretamente,
            tempo_de_ida_e_volta_em_segundos,
            soma_recebida_do_servidor,
            soma_esperada_calculada_localmente,
        ) = resultados_de_todos_os_clientes[identificador_do_cliente]

        texto_do_status = "OK" if servidor_respondeu_corretamente else "ERRO"

        # Basta um cliente errado para o resultado geral ser "com erros".
        todos_os_clientes_receberam_soma_correta = (
            todos_os_clientes_receberam_soma_correta and servidor_respondeu_corretamente
        )

        print(
            f"[CLIENTE {identificador_do_cliente:02d}] {texto_do_status} | "
            f"soma recebida={soma_recebida_do_servidor} | "
            f"esperada={soma_esperada_calculada_localmente} | "
            f"ida e volta={tempo_de_ida_e_volta_em_segundos:.6f}s"
        )

    print(
        "[CLIENTE] Todos corretos."
        if todos_os_clientes_receberam_soma_correta
        else "[CLIENTE] Houve erros!"
    )

    # Código de saída: 0 = sucesso, 1 = houve erro. O run_all.sh usa isso para
    # parar caso algum cenário falhe.
    sys.exit(0 if todos_os_clientes_receberam_soma_correta else 1)


# Só executa main() se o arquivo for rodado diretamente (python3 client.py),
# e não quando for apenas importado por outro arquivo.
if __name__ == "__main__":
    main()