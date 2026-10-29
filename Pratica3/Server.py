"""
Servidor TCP multithread.

Para cada cliente conectado, uma thread:
  1. lê o cabeçalho (quantidade de números);
  2. lê os números (uint16, big-endian);
  3. soma todos;
  4. devolve a soma (uint64, big-endian).

Mede o tempo de computação por cliente e o tempo total de cada "lote"
(conjunto de clientes simultâneos).
"""

# ---------------------------------------------------------------------------
# IMPORTAÇÕES (todas da biblioteca padrão do Python, nada para instalar)
# ---------------------------------------------------------------------------
import argparse    # lê argumentos da linha de comando (--host, --port)
import csv         # escreve o arquivo CSV com os resultados
import os          # manipula caminhos e pastas do sistema de arquivos
import socket      # comunicação de rede via TCP
import struct      # converte números em bytes (e vice-versa) com formato fixo
import sys         # informações do sistema (aqui: ordem dos bytes da máquina)
import threading   # permite atender vários clientes ao mesmo tempo (threads)
import time        # relógio de alta precisão para medir os tempos
from array import array  # vetor compacto de números inteiros de tamanho fixo


# ---------------------------------------------------------------------------
# CONSTANTES DO PROTOCOLO DE COMUNICAÇÃO
# ---------------------------------------------------------------------------

# Formato do cabeçalho enviado pelo cliente: um inteiro SEM sinal de 4 bytes
# que informa QUANTOS números virão em seguida.
#   "!" = ordem de bytes de rede (big-endian)
#   "I" = unsigned int (4 bytes)
FORMATO_CABECALHO_QUANTIDADE_NUMEROS = struct.Struct("!I")

# Formato da resposta enviada pelo servidor: um inteiro SEM sinal de 8 bytes
# com a SOMA TOTAL dos números (1.000.000 x 1000 = 1 bilhão não cabe em 4
# bytes com folga, por isso usamos 8).
#   "Q" = unsigned long long (8 bytes)
FORMATO_RESPOSTA_SOMA_TOTAL = struct.Struct("!Q")

# Cada número (0 a 1000) é enviado ocupando 2 bytes (uint16).
BYTES_POR_NUMERO_ENVIADO = 2


# ---------------------------------------------------------------------------
# ESTADO COMPARTILHADO ENTRE AS THREADS
# ---------------------------------------------------------------------------

# Trava (mutex): só UMA thread por vez pode mexer no dicionário abaixo.
# Sem ela, duas threads poderiam alterar os contadores ao mesmo tempo e
# corromper os valores (condição de corrida).
trava_estado_compartilhado = threading.Lock()

# Dicionário que todas as threads leem e escrevem (sempre protegido pela trava).
estado_compartilhado = {
    # Quantas conexões de clientes estão abertas neste exato momento.
    # Quando volta a 0, sabemos que o "lote" de clientes terminou.
    "conexoes_ativas_agora": 0,

    # Quantos clientes participaram do lote atual (é o número que vai para o
    # CSV: 1, 4, 8 ou 16).
    "quantidade_de_clientes_no_lote_atual": 0,

    # Instante (em segundos, relógio perf_counter) em que o PRIMEIRO cliente
    # do lote começou a enviar dados. É o marco zero do tempo total do lote.
    # None significa "o lote ainda não começou".
    "instante_inicio_do_primeiro_cliente_do_lote": None,
}

# Local onde os tempos de cada lote serão gravados.
CAMINHO_ARQUIVO_CSV_RESULTADOS = os.path.join("resultados", "servidor.csv")


# ---------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: LER UMA QUANTIDADE EXATA DE BYTES DO SOCKET
# ---------------------------------------------------------------------------
def receber_exatamente_n_bytes(conexao_socket_do_cliente, quantidade_de_bytes_esperada):
    """Lê exatamente `quantidade_de_bytes_esperada` bytes do socket.

    O TCP é um fluxo contínuo de bytes: uma única chamada de recv pode devolver
    menos bytes do que o pedido (os dados chegam em pedaços). Por isso repetimos
    a leitura até completar a quantidade desejada.
    """
    # Cria um bloco de memória já com o tamanho final, preenchido com zeros.
    # Os bytes recebidos serão gravados diretamente dentro dele.
    buffer_de_bytes_recebidos = bytearray(quantidade_de_bytes_esperada)

    # "Visão" do buffer que permite gravar em uma parte dele sem copiar dados.
    visao_do_buffer = memoryview(buffer_de_bytes_recebidos)

    # Quantos bytes já foram recebidos até agora.
    total_de_bytes_ja_recebidos = 0

    # Repete até receber tudo o que foi pedido.
    while total_de_bytes_ja_recebidos < quantidade_de_bytes_esperada:
        # Recebe direto no buffer, a partir da posição onde paramos.
        # Devolve quantos bytes chegaram nesta leitura.
        bytes_recebidos_nesta_leitura = conexao_socket_do_cliente.recv_into(
            visao_do_buffer[total_de_bytes_ja_recebidos:],
            quantidade_de_bytes_esperada - total_de_bytes_ja_recebidos,
        )

        # Se recv devolver 0, o cliente fechou a conexão antes de enviar tudo.
        if bytes_recebidos_nesta_leitura == 0:
            raise ConnectionError("Conexão encerrada antes de receber todos os dados")

        total_de_bytes_ja_recebidos += bytes_recebidos_nesta_leitura

    return buffer_de_bytes_recebidos


# ---------------------------------------------------------------------------
# FUNÇÃO AUXILIAR: GRAVAR O RESULTADO DE UM LOTE NO CSV
# ---------------------------------------------------------------------------
def salvar_resultado_do_lote_no_csv(quantidade_de_clientes_no_lote,
                                    tempo_total_do_lote_em_segundos):
    """Acrescenta uma linha (clientes, tempo total) ao arquivo CSV."""
    # Cria a pasta "resultados" caso ela ainda não exista.
    os.makedirs("resultados", exist_ok=True)

    # Verifica se o arquivo é novo, para saber se precisa escrever o cabeçalho.
    arquivo_csv_ainda_nao_existe = not os.path.exists(CAMINHO_ARQUIVO_CSV_RESULTADOS)

    # Abre em modo "a" (append): adiciona ao final sem apagar o que já existe.
    with open(CAMINHO_ARQUIVO_CSV_RESULTADOS, "a", newline="") as arquivo_csv_aberto:
        escritor_de_linhas_csv = csv.writer(arquivo_csv_aberto)

        # Primeira escrita: linha com os nomes das colunas.
        if arquivo_csv_ainda_nao_existe:
            escritor_de_linhas_csv.writerow(["clientes", "tempo_total_servidor_s"])

        # Linha de dados, com o tempo formatado com 6 casas decimais.
        escritor_de_linhas_csv.writerow(
            [quantidade_de_clientes_no_lote, f"{tempo_total_do_lote_em_segundos:.6f}"]
        )


# ---------------------------------------------------------------------------
# FUNÇÃO EXECUTADA POR CADA THREAD: ATENDE UM CLIENTE
# ---------------------------------------------------------------------------
def atender_cliente(conexao_com_o_cliente, endereco_do_cliente):
    """Atende UM cliente do início ao fim. Roda em uma thread própria."""
    try:
        # O "with" garante que a conexão será fechada ao terminar o bloco.
        with conexao_com_o_cliente:

            # -----------------------------------------------------------
            # ETAPA 1: LER O CABEÇALHO (quantos números virão)
            # -----------------------------------------------------------
            # Só chega quando o cliente começa a enviar (após a barreira).
            quantidade_de_numeros_que_o_cliente_vai_enviar = (
                FORMATO_CABECALHO_QUANTIDADE_NUMEROS.unpack(
                    receber_exatamente_n_bytes(
                        conexao_com_o_cliente,
                        FORMATO_CABECALHO_QUANTIDADE_NUMEROS.size,
                    )
                )[0]  # unpack devolve uma tupla; pegamos o primeiro (único) item
            )

            # Marca o instante em que ESTE cliente começou a ser processado.
            instante_inicio_deste_cliente = time.perf_counter()

            # Se este for o primeiro cliente do lote a começar, ele define o
            # marco zero do tempo total do lote.
            with trava_estado_compartilhado:
                if estado_compartilhado["instante_inicio_do_primeiro_cliente_do_lote"] is None:
                    estado_compartilhado["instante_inicio_do_primeiro_cliente_do_lote"] = (
                        instante_inicio_deste_cliente
                    )

            # -----------------------------------------------------------
            # ETAPA 2: RECEBER OS NÚMEROS
            # -----------------------------------------------------------
            # Total de bytes = quantidade de números x 2 bytes cada.
            bytes_brutos_dos_numeros_recebidos = receber_exatamente_n_bytes(
                conexao_com_o_cliente,
                quantidade_de_numeros_que_o_cliente_vai_enviar * BYTES_POR_NUMERO_ENVIADO,
            )

            # Cria um vetor de inteiros de 2 bytes sem sinal ("H" = uint16) e
            # o preenche com os bytes recebidos, interpretando-os como números.
            vetor_com_os_numeros_recebidos = array("H")
            vetor_com_os_numeros_recebidos.frombytes(bytes_brutos_dos_numeros_recebidos)

            # A rede usa big-endian. Se esta máquina usa little-endian (a
            # maioria dos PCs), é preciso inverter os bytes de cada número,
            # senão os valores ficariam errados (ex.: 1 viraria 256).
            if sys.byteorder == "little":
                vetor_com_os_numeros_recebidos.byteswap()

            # -----------------------------------------------------------
            # ETAPA 3: SOMAR TODOS OS NÚMEROS
            # -----------------------------------------------------------
            soma_total_dos_numeros_recebidos = sum(vetor_com_os_numeros_recebidos)

            # -----------------------------------------------------------
            # ETAPA 4: DEVOLVER A SOMA PARA O CLIENTE
            # -----------------------------------------------------------
            # Converte a soma em 8 bytes (formato de rede) e envia tudo.
            conexao_com_o_cliente.sendall(
                FORMATO_RESPOSTA_SOMA_TOTAL.pack(soma_total_dos_numeros_recebidos)
            )

            # Marca o fim do atendimento deste cliente (resposta já enviada).
            instante_fim_deste_cliente = time.perf_counter()

            # Mostra no terminal o resumo deste cliente.
            print(
                f"[SERVIDOR] {endereco_do_cliente[0]}:{endereco_do_cliente[1]} | "
                f"números={quantidade_de_numeros_que_o_cliente_vai_enviar} | "
                f"soma={soma_total_dos_numeros_recebidos} | "
                f"tempo={instante_fim_deste_cliente - instante_inicio_deste_cliente:.6f}s",
                flush=True,  # força a exibição imediata, sem esperar o buffer
            )

    except Exception as erro_ocorrido:
        # Qualquer falha com este cliente é registrada, sem derrubar o servidor.
        print(f"[SERVIDOR] Erro com {endereco_do_cliente}: {erro_ocorrido}", flush=True)

    finally:
        # O "finally" sempre executa (com sucesso ou erro), então a contagem
        # de conexões ativas fica sempre correta.
        with trava_estado_compartilhado:
            estado_compartilhado["conexoes_ativas_agora"] -= 1

            # Se não restou nenhuma conexão ativa, o lote inteiro terminou:
            # é hora de calcular e registrar o tempo total.
            lote_terminou = (
                estado_compartilhado["conexoes_ativas_agora"] == 0
                and estado_compartilhado["instante_inicio_do_primeiro_cliente_do_lote"] is not None
            )
            if lote_terminou:
                # Tempo total = agora - início do primeiro cliente do lote.
                tempo_total_do_lote_em_segundos = (
                    time.perf_counter()
                    - estado_compartilhado["instante_inicio_do_primeiro_cliente_do_lote"]
                )
                quantidade_de_clientes_no_lote_finalizado = (
                    estado_compartilhado["quantidade_de_clientes_no_lote_atual"]
                )

                print(
                    f"[SERVIDOR] >>> LOTE FINALIZADO: "
                    f"{quantidade_de_clientes_no_lote_finalizado} cliente(s) | "
                    f"tempo total = {tempo_total_do_lote_em_segundos:.6f}s\n",
                    flush=True,
                )

                # Grava no CSV.
                salvar_resultado_do_lote_no_csv(
                    quantidade_de_clientes_no_lote_finalizado,
                    tempo_total_do_lote_em_segundos,
                )

                # Zera o estado para o próximo lote começar do zero.
                estado_compartilhado["instante_inicio_do_primeiro_cliente_do_lote"] = None
                estado_compartilhado["quantidade_de_clientes_no_lote_atual"] = 0


# ---------------------------------------------------------------------------
# FUNÇÃO PRINCIPAL: CONFIGURA O SERVIDOR E ACEITA CLIENTES
# ---------------------------------------------------------------------------
def main():
    # --- Leitura dos argumentos da linha de comando ---
    leitor_de_argumentos_da_linha_de_comando = argparse.ArgumentParser(
        description="Servidor de soma multithread"
    )
    # Endereço em que o servidor escuta. "0.0.0.0" = todas as interfaces de
    # rede da máquina (aceita conexões locais e de outras máquinas).
    leitor_de_argumentos_da_linha_de_comando.add_argument("--host", default="0.0.0.0")
    # Porta TCP em que o servidor escuta.
    leitor_de_argumentos_da_linha_de_comando.add_argument("--port", type=int, default=5000)
    argumentos_recebidos = leitor_de_argumentos_da_linha_de_comando.parse_args()

    # --- Criação do socket do servidor ---
    # AF_INET = IPv4; SOCK_STREAM = TCP.
    socket_de_escuta_do_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Permite reutilizar a porta imediatamente após fechar o servidor, evitando
    # o erro "Address already in use" ao reiniciar.
    socket_de_escuta_do_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Associa o socket ao endereço e porta escolhidos.
    socket_de_escuta_do_servidor.bind((argumentos_recebidos.host, argumentos_recebidos.port))

    # Começa a escutar. 64 = tamanho da fila de conexões aguardando aceitação
    # (folga suficiente para os 16 clientes simultâneos).
    socket_de_escuta_do_servidor.listen(64)

    print(
        f"[SERVIDOR] Escutando em {argumentos_recebidos.host}:{argumentos_recebidos.port} "
        f"(Ctrl+C para sair)",
        flush=True,
    )

    try:
        # Laço infinito: o servidor fica aceitando clientes até ser interrompido.
        while True:
            # accept() bloqueia até um cliente conectar. Devolve um NOVO socket
            # exclusivo para falar com esse cliente e o endereço dele.
            conexao_com_o_cliente_aceito, endereco_do_cliente_aceito = (
                socket_de_escuta_do_servidor.accept()
            )

            # Registra o novo cliente ANTES de iniciar a thread, para que a
            # contagem de conexões ativas já esteja correta e o lote não seja
            # finalizado por engano.
            with trava_estado_compartilhado:
                estado_compartilhado["conexoes_ativas_agora"] += 1
                estado_compartilhado["quantidade_de_clientes_no_lote_atual"] += 1

            # MULTITHREAD: cria uma thread só para este cliente e a inicia.
            # O laço volta imediatamente a aceitar o próximo cliente, enquanto
            # a thread atende este em paralelo.
            #   daemon=True -> a thread não impede o programa de encerrar.
            threading.Thread(
                target=atender_cliente,
                args=(conexao_com_o_cliente_aceito, endereco_do_cliente_aceito),
                daemon=True,
            ).start()

    except KeyboardInterrupt:
        # Ctrl+C no terminal: encerra de forma limpa.
        print("\n[SERVIDOR] Encerrado.")

    finally:
        # Sempre fecha o socket de escuta ao sair.
        socket_de_escuta_do_servidor.close()


# Só executa main() se o arquivo for rodado diretamente (python3 server.py),
# e não quando for apenas importado por outro arquivo.
if __name__ == "__main__":
    main()
