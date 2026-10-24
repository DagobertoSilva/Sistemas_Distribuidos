# Terceira Prática – Sistemas Distribuídos

**Universidade Federal do Ceará – Campus de Crateús**
**Disciplina:** Sistemas Distribuídos
**Professor:** Anderson Almada

Cliente e servidor TCP **multithread** em Python. Cada cliente envia **1.000.000 de números aleatórios (0 a 1000)** ao servidor, que soma todos e devolve o resultado. O projeto é executado com **1, 4, 8 e 16 clientes simultâneos** e o tempo de computação do servidor é medido em cada caso.

---

## Sumário

1. [O que o enunciado pede](#1-o-que-o-enunciado-pede)
2. [Visão geral da solução](#2-visão-geral-da-solução)
3. [Pré-requisitos](#3-pré-requisitos)
4. [Estrutura do projeto](#4-estrutura-do-projeto)
5. [Passo a passo da implementação](#5-passo-a-passo-da-implementação)
6. [Como executar](#6-como-executar)
7. [Como o tempo é medido](#7-como-o-tempo-é-medido)
8. [Resultados](#8-resultados)
9. [Análise dos resultados](#9-análise-dos-resultados)
10. [Problemas comuns](#10-problemas-comuns)
11. [Roteiro para o vídeo](#11-roteiro-para-o-vídeo)
12. [Publicando no GitHub](#12-publicando-no-github)

---

## 1. O que o enunciado pede

| Requisito | Como foi atendido |
|---|---|
| Processo cliente e processo servidor | `client.py` e `server.py`, executados em terminais separados |
| Servidor usando multithread | O servidor cria **uma thread para cada cliente** conectado |
| Cliente envia 1.000.000 de números aleatórios entre 0 e 1000 | `client.py` gera os números com `random` e envia todos pela rede |
| Servidor soma e devolve a resposta | Servidor calcula a soma e envia de volta 8 bytes com o total |
| Executar com 1, 4, 8 e 16 clientes simultâneos | Parâmetro `--clients` e o script `run_all.sh` |
| Medir o tempo do servidor para toda a computação | Servidor registra o tempo por cliente e o tempo total de cada lote |
| Entregar zip ou GitHub + vídeo | Seções [12](#12-publicando-no-github) e [11](#11-roteiro-para-o-vídeo) |

---

## 2. Visão geral da solução

```
 Cliente 1 ──┐
 Cliente 2 ──┤                       ┌─ Thread 1 ─ recebe, soma, responde
    ...      ├──►  SERVIDOR (TCP) ───┼─ Thread 2 ─ recebe, soma, responde
 Cliente N ──┘   (thread por cliente)└─ Thread N ─ recebe, soma, responde
```

**Fluxo de uma conexão:**

1. O cliente gera 1.000.000 de números aleatórios e calcula localmente a soma esperada (para conferir depois).
2. O cliente abre a conexão TCP com o servidor.
3. Todos os clientes esperam numa **barreira** (`threading.Barrier`) para começarem a enviar **ao mesmo tempo**. Isso garante simultaneidade real.
4. O cliente envia: `[4 bytes: quantidade de números][2 bytes × quantidade: os números]`.
5. A thread do servidor lê tudo, soma e responde com `[8 bytes: soma total]`.
6. O cliente compara a soma recebida com a soma esperada e imprime `OK` ou `ERRO`.

**Decisões de projeto:**

- **TCP (`socket`)**: confiável e ordenado, ideal para enviar um bloco grande de dados.
- **Protocolo binário**: cada número entre 0 e 1000 cabe em 2 bytes (`uint16`). Os 1.000.000 de números ocupam cerca de 2 MB, bem mais leve que enviar texto.
- **Cabeçalho com a quantidade**: o servidor sabe exatamente quantos bytes ler.
- **Thread por conexão**: simples de entender e atende o requisito de multithread.
- **Apenas biblioteca padrão**: não precisa instalar nada.

---

## 3. Pré-requisitos

- **Python 3.8 ou superior**
- Linux, macOS ou Windows (no Windows, use o PowerShell ou o Git Bash para o `run_all.sh`)

Verifique a versão:

```bash
python3 --version
```

Nenhuma dependência externa é necessária.

---

## 4. Estrutura do projeto

```
terceira-pratica/
├── server.py        # Servidor TCP multithread
├── client.py        # Cliente (executa N clientes simultâneos em threads)
├── run_all.sh       # Roda automaticamente 1, 4, 8 e 16 clientes
├── resultados/      # Saídas dos testes (CSV)
└── README.md
```

---

## 5. Passo a passo da implementação

### Passo 1 – Criar a pasta do projeto

```bash
mkdir terceira-pratica
cd terceira-pratica
mkdir resultados
```

### Passo 2 – Criar o servidor (`server.py`)



```python
#!/usr/bin/env python3
# A linha acima (shebang) permite executar o arquivo diretamente no Linux/macOS
# com "./server.py", usando o interpretador python3 do sistema.

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
```

**Explicação das partes principais:**

| Trecho | O que faz |
|---|---|
| `HEADER` / `RESPONSE` | Formatos binários do protocolo (`!I` = inteiro de 4 bytes, `!Q` = inteiro de 8 bytes, `!` = ordem de bytes da rede). |
| `recv_exact` | O TCP é um fluxo de bytes e `recv` pode devolver menos do que o pedido. Essa função repete a leitura até completar o tamanho exato. |
| `array("H")` | Vetor de inteiros de 2 bytes sem sinal (0 a 65535), suficiente para 0 a 1000. |
| `byteswap()` | Converte de big-endian (rede) para a ordem da máquina, se necessário. |
| `lock` | Protege as variáveis compartilhadas entre as threads (contadores e instante inicial do lote). |
| `threading.Thread(...)` | **Multithread**: cada cliente aceito é atendido por uma thread própria, em paralelo com as outras. |
| `state["active"]` | Quando chega a 0, todos os clientes do lote terminaram e o tempo total é registrado. |

### Passo 3 – Criar o cliente (`client.py`)

Crie o arquivo `client.py`.

```python
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
    barreira_de_sincronizacao_entre_clientes = threading.Barrier(argumentos_recebidos.clients)

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
```

**Explicação das partes principais:**

| Trecho | O que faz |
|---|---|
| `random.choices(range(0, 1001), k=quantity)` | Sorteia 1.000.000 de inteiros entre 0 e 1000 (inclusive). |
| `expected = sum(numbers)` | Soma local usada para **validar** a resposta do servidor. |
| `threading.Barrier(N)` | Todos os clientes só prosseguem quando os N chegaram. Garante que o envio começa ao mesmo tempo. |
| `sock.sendall(payload)` | Envia cabeçalho + 2 MB de números em uma única operação. |
| `RESPONSE.unpack(...)` | Decodifica os 8 bytes com a soma enviada pelo servidor. |

> **Por que clientes em threads e não em processos?** Cada thread abre sua própria conexão TCP, então o servidor enxerga N clientes independentes. A geração dos números é feita **antes** da barreira, portanto não interfere na medição.




---

## 6. Como executar

### Passo 5 – Iniciar o servidor (Terminal 1)

```bash
python3 server.py
```

Saída esperada:

```
[SERVIDOR] Escutando em 0.0.0.0:5000 (Ctrl+C para sair)
```

Deixe esse terminal aberto.

### Passo 6 – Teste rápido com 1 cliente (Terminal 2)

```bash
python3 client.py --clients 1
```

Saída esperada (os tempos variam):

```
[CLIENTE] Iniciando 1 cliente(s) simultâneo(s)...
[CLIENTE 00] OK | soma recebida=500123456 | esperada=500123456 | ida e volta=0.015000s
[CLIENTE] Todos corretos.
```

E no terminal do servidor:

```
[SERVIDOR] 127.0.0.1:54321 | números=1000000 | soma=500123456 | tempo=0.012000s
[SERVIDOR] >>> LOTE FINALIZADO: 1 cliente(s) | tempo total = 0.012000s
```

> A soma deve ficar perto de **500.000.000** (1.000.000 × média de 500).



Ou manualmente, um por vez:

```bash
python3 client.py --clients 1
```

```bash
python3 client.py --clients 4
```

```bash
python3 client.py --clients 8
```

```bash
python3 client.py --clients 16
```

### Passo 8 – Coletar os tempos

Cada linha `LOTE FINALIZADO` no terminal do servidor traz o tempo total do cenário. Os mesmos dados são gravados em `resultados/servidor.csv`:

```bash
cat resultados/servidor.csv
```

```
clientes,tempo_total_servidor_s
1,0.012000
4,0.050000
8,0.098000
16,0.195000
```



### Executando em máquinas diferentes (opcional)

Servidor na máquina A, clientes na máquina B:

```bash
# Máquina A
python3 server.py --host 0.0.0.0 --port 5000

# Máquina B (troque pelo IP da máquina A)
python3 client.py --host 192.168.0.10 --port 5000 --clients 8
```

Libere a porta 5000 no firewall da máquina A, se necessário.

---

## 7. Como o tempo é medido

O enunciado pede: *"verifique quanto tempo o servidor levou para realizar toda a computação"*. Foram medidos dois valores, ambos **no servidor**, com `time.perf_counter()`:

| Métrica | Início | Fim |
|---|---|---|
| **Tempo por cliente** | Chegada do cabeçalho | Resposta enviada |
| **Tempo total do lote** (principal) | Início do **primeiro** cliente do lote | Fim do **último** cliente do lote |

O **tempo total do lote** é o que deve ser usado para comparar 1, 4, 8 e 16 clientes, pois representa quanto o servidor levou para concluir **toda** a computação daquele cenário.

Um lote é considerado finalizado quando o contador de conexões ativas chega a zero.

---

## 8. Resultados

Preencha com os valores medidos na sua máquina (média de várias execuções):

| Nº de clientes | Total de números processados | Tempo total no servidor (s) | Tempo médio por cliente (s) |
|:---:|:---:|:---:|:---:|
| 1  | 1.000.000  | 0,026006 | 0,025456 |
| 4  | 4.000.000  | 0,089421 | 0,085615 |
| 8  | 8.000.000  | 0,185083 | 0,070652 |
| 16 | 16.000.000 | 0,348325 | 0,196040 |



---

## 9. Análise dos resultados

Pontos para discutir ao comparar os cenários:

1. **Crescimento do tempo com o número de clientes.** Com mais clientes, o servidor recebe e soma mais dados (4, 8, 16 vezes mais). É esperado que o tempo total aumente.
2. **Escalabilidade.** Compare: se dobrar os clientes, o tempo dobra, ou cresce menos? Crescimento menor que o proporcional indica que o servidor aproveita a concorrência (por exemplo, enquanto uma thread espera dados da rede, outra computa).
3. **Limitação do GIL (Global Interpreter Lock) no Python.** Em CPython, só uma thread executa código Python por vez. A soma de cada cliente é feita em Python puro, então a parte de cálculo é serializada. O ganho da concorrência vem principalmente da **sobreposição de operações de E/S** (receber dados pela rede), pois o GIL é liberado durante `recv`. Em linguagens sem essa restrição (C, Java, Go) ou usando `multiprocessing`, a soma também executaria em paralelo real nos vários núcleos.
4. **Rede local (loopback).** Rodando tudo na mesma máquina, a rede é muito rápida e os clientes disputam a mesma CPU do servidor. Em máquinas separadas os números tendem a refletir melhor o custo de transferência.
5. **Custo de transferência.** Cada cliente envia cerca de 2 MB; com 16 clientes, são cerca de 32 MB trafegando para o servidor.
6. **Variação entre execuções.** Escalonamento do sistema operacional e outros programas abertos causam oscilações. Por isso, use a média de várias execuções.

---
