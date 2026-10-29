# Calculadora gRPC

**Universidade Federal do Ceará – Campus de Crateús**
**Disciplina:** Sistemas Distribuídos
**Professor:** Anderson Almada
**Atividade:** Quarta Prática

---

## Sumário

1. [Enunciado](#1-enunciado)
2. [Visão geral da solução](#2-visão-geral-da-solução)
3. [Conceitos fundamentais (Aula 13)](#3-conceitos-fundamentais-aula-13)
4. [Arquitetura e fluxo de uma chamada](#4-arquitetura-e-fluxo-de-uma-chamada)
5. [Estrutura do projeto](#5-estrutura-do-projeto)
6. [Pré-requisitos](#6-pré-requisitos)
7. [Passo a passo para construir o projeto do zero](#7-passo-a-passo-para-construir-o-projeto-do-zero)
8. [Como executar (projeto já pronto)](#8-como-executar-projeto-já-pronto)
9. [Exemplo de execução](#9-exemplo-de-execução)
10. [Tratamento de erros](#10-tratamento-de-erros)
11. [Decisões de projeto](#11-decisões-de-projeto)
12. [Testes manuais sugeridos](#12-testes-manuais-sugeridos)
13. [Roteiro sugerido para o vídeo](#13-roteiro-sugerido-para-o-vídeo)
14. [Entrega](#14-entrega)
15. [Solução de problemas](#15-solução-de-problemas)
16. [Possíveis melhorias futuras](#16-possíveis-melhorias-futuras)
17. [Autor](#17-autor)

---

## 1. Enunciado

> Crie uma calculadora em gRPC com as funcionalidades de **soma, subtração, multiplicação e divisão de três números**. Entregar o projeto em formato zip ou repositório (GitHub) e um vídeo explicando todo o funcionamento.

### Requisitos extraídos do enunciado

| # | Requisito | Como foi atendido |
|---|-----------|-------------------|
| 1 | Usar **gRPC** | Comunicação cliente-servidor com `grpcio` e Protocol Buffers |
| 2 | Operação de **soma** | RPC `Somar` |
| 3 | Operação de **subtração** | RPC `Subtrair` |
| 4 | Operação de **multiplicação** | RPC `Multiplicar` |
| 5 | Operação de **divisão** | RPC `Dividir` |
| 6 | Cada operação recebe **três números** | Mensagem `OperacaoRequest` com `numero1`, `numero2` e `numero3` |
| 7 | Entrega em **zip ou GitHub** | Ver [seção 14](#14-entrega) |
| 8 | **Vídeo** explicando o funcionamento | Ver [roteiro na seção 13](#13-roteiro-sugerido-para-o-vídeo) |

---

## 2. Visão geral da solução

O projeto é uma aplicação **cliente-servidor** em que:

- O **servidor** (`servidor.py`) expõe o serviço `Calculadora` com quatro métodos remotos.
- O **cliente** (`cliente.py`) mostra um menu no terminal, lê três números, escolhe a operação e chama o método remoto correspondente.
- Toda a comunicação usa **gRPC** sobre **HTTP/2**, com mensagens serializadas em **Protocol Buffers**.

A linguagem adotada é **Python 3**, a mesma usada na demonstração da Aula 13. O mesmo arquivo `.proto` poderia ser usado para gerar cliente e servidor em Java, Go, C++, Node.js etc.

> **Base:** este projeto estende a demonstração da Aula 13, que implementa apenas `Somar` com **dois** números, para quatro operações com **três** números.

---

## 3. Conceitos fundamentais (Aula 13)

### 3.1 O que é gRPC?

- **RPC** (*Remote Procedure Call*): chamada de métodos entre processos. O cliente chama uma função que executa em outro processo ou máquina como se fosse local.
- **Baseado em HTTP/2**: multiplexação e comunicação bidirecional.
- **Protocol Buffers**: serialização de dados em formato binário.
- **Multiplataforma**: suporte a diversas linguagens.

### 3.2 Vantagens do gRPC

| Vantagem | Descrição |
|----------|-----------|
| Alto desempenho | Mensagens em formato binário e menor *overhead* |
| Multiplataforma | Cliente e servidor podem usar linguagens diferentes |
| Streaming | Suporte a *unary*, *server*, *client* e *bidirectional streaming* |
| Geração de código | Criação automática de clientes e servidores a partir do `.proto` |

### 3.3 Protocol Buffers (protobuf)

Um arquivo `.proto` define:

- **`message`**: uma estrutura de dados. Cada campo tem um **tipo** (`int32`, `string`, `double`, `bool`...) e um **número único**, que identifica o campo na serialização binária.
- **`service`**: o conjunto de métodos RPC, com seus tipos de requisição e resposta.

O compilador `protoc` lê o `.proto` e **gera o código** de mensagens, cliente (*stub*) e servidor (*servicer*).

### 3.4 HTTP/2

| Recurso | O que significa |
|---------|-----------------|
| Multiplexação | Várias requisições na mesma conexão TCP |
| *Streams* | Requisições e respostas em paralelo |
| Cabeçalhos comprimidos | Menor uso de banda (HPACK) |
| Comunicação segura | Utiliza TLS (opcional) |

### 3.5 Tipos de comunicação gRPC

| Tipo | Descrição |
|------|-----------|
| **Unary** (unária) | O cliente envia uma requisição e recebe uma única resposta |
| Server streaming | O cliente envia uma requisição e o servidor envia várias respostas |
| Client streaming | O cliente envia várias requisições e o servidor retorna uma única resposta |
| Bidirectional streaming | Cliente e servidor trocam várias mensagens de forma independente e simultânea |

**Este trabalho usa o modo Unary:** o cliente envia **uma** mensagem com os três números e recebe **uma** mensagem com o resultado.

### 3.6 gRPC vs REST

| Aspecto | gRPC | REST |
|---------|------|------|
| Formato de dados | Protocol Buffers (binário e compacto) | JSON (texto) ou XML |
| Protocolo | HTTP/2 | HTTP/1.1 ou HTTP/2 |
| Definição de serviço | Arquivo `.proto` com geração automática de código | Convenções de recursos (URLs e verbos HTTP) |
| Desempenho | Menor latência e menor uso de banda | Maior *overhead* e maior latência |
| Uso típico | Microsserviços e sistemas distribuídos | APIs públicas e integração com navegadores |

---

## 4. Arquitetura e fluxo de uma chamada

```
┌──────────────────────┐                        ┌──────────────────────────┐
│       CLIENTE        │                        │         SERVIDOR         │
│    (cliente.py)      │                        │       (servidor.py)      │
│                      │                        │                          │
│  1. Lê os 3 números  │   OperacaoRequest      │  3. Executa a operação   │
│  2. Chama o stub ────┼───────────────────────►│     em CalculadoraServicer│
│     (ex.: Somar)     │   HTTP/2 + Protobuf    │                          │
│                      │                        │                          │
│  5. Exibe resultado  │◄───────────────────────┼─ 4. Retorna              │
│                      │   OperacaoResponse     │     OperacaoResponse     │
└──────────────────────┘                        └──────────────────────────┘
         ▲                                                    ▲
         │                                                    │
   calculadora_pb2.py / calculadora_pb2_grpc.py (gerados a partir de calculadora.proto)
```

**Os 4 passos de uma chamada gRPC:**

1. **Serialização:** o cliente chama o método do *stub*, que serializa a requisição em Protocol Buffers.
2. **Transporte:** a requisição é enviada via HTTP/2 em um *stream*.
3. **Processamento:** o servidor desserializa a requisição, executa o método e serializa a resposta.
4. **Resposta:** a resposta volta pelo mesmo *stream*, em formato binário.

---

## 5. Estrutura do projeto

```
calc-grpc/
├── calculadora.proto          # Contrato do serviço (mensagens + RPCs)
├── calculadora_pb2.py         # (gerado) classes das mensagens
├── calculadora_pb2_grpc.py    # (gerado) stub e servicer base
├── servidor.py                # Implementação do servidor
├── cliente.py                 # Cliente interativo (menu no terminal)
├── requirements.txt           # Dependências
├── .gitignore                 # Ignora venv/ e __pycache__/
└── README.md                  # Este arquivo
```

> Os arquivos `calculadora_pb2.py` e `calculadora_pb2_grpc.py` são **gerados** pelo `protoc` (passo 5) e **nunca** devem ser editados manualmente.

---

## 6. Pré-requisitos

- **Python 3.8+** (confira com `python3 --version`)
- **pip** (confira com `pip --version`)
- Um editor de código (VS Code, por exemplo)
- (Opcional) **Git**, para publicar no GitHub

---

## 7. Passo a passo para construir o projeto do zero

Siga os passos na ordem. Cada passo diz **o que fazer**, **o comando/código** e **como verificar**.

### Passo 1 – Criar a pasta do projeto

```bash
mkdir calc-grpc
cd calc-grpc
```

✅ **Verificação:** `pwd` (Linux/macOS) ou `cd` (Windows) deve mostrar a pasta `calc-grpc`.

---

### Passo 2 – Criar e ativar o ambiente virtual

O ambiente virtual isola as dependências deste projeto.

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (CMD):**

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

✅ **Verificação:** o terminal passa a mostrar `(venv)` no início da linha.

> No PowerShell, se aparecer erro de política de execução, rode antes: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`

---

### Passo 3 – Instalar as dependências

```bash
pip install grpcio grpcio-tools
```

- `grpcio`: biblioteca de execução do gRPC (usada por cliente e servidor).
- `grpcio-tools`: traz o compilador `protoc` para Python.

Salve as dependências em um arquivo:

```bash
pip freeze > requirements.txt
```

✅ **Verificação:** `pip list` deve listar `grpcio`, `grpcio-tools` e `protobuf`.

---

### Passo 4 – Abrir o projeto no editor e criar o contrato (`calculadora.proto`)

```bash
code .
```

Crie o arquivo **`calculadora.proto`** na raiz com o conteúdo:

```protobuf
syntax = "proto3";

package calculadora;

// Serviço remoto com as quatro operações
service Calculadora {
  rpc Somar       (OperacaoRequest) returns (OperacaoResponse);
  rpc Subtrair    (OperacaoRequest) returns (OperacaoResponse);
  rpc Multiplicar (OperacaoRequest) returns (OperacaoResponse);
  rpc Dividir     (OperacaoRequest) returns (OperacaoResponse);
}

// Requisição: os três operandos
message OperacaoRequest {
  double numero1 = 1;
  double numero2 = 2;
  double numero3 = 3;
}

// Resposta: o resultado da operação
message OperacaoResponse {
  double resultado = 1;
}


```

**Explicação linha a linha:**

| Trecho | Significado |
|--------|-------------|
| `syntax = "proto3";` | Usa a versão 3 do Protocol Buffers |
| `package calculadora;` | Namespace do contrato, evitando conflitos de nomes |
| `service Calculadora { ... }` | Declara o serviço remoto e seus métodos |
| `rpc Somar (OperacaoRequest) returns (OperacaoResponse);` | Método que recebe `OperacaoRequest` e devolve `OperacaoResponse` |
| `message OperacaoRequest` | Estrutura com os três operandos |
| `double` | Ponto flutuante de 64 bits (aceita decimais e divisões não exatas) |
| `= 1`, `= 2`, `= 3` | **Números de campo**: identificam o campo no formato binário (**não** são valores) |

**Por que uma única mensagem para as quatro operações?**
Todas têm a mesma entrada (três números) e a mesma saída (um número). Reutilizar as mensagens evita duplicação.

---

### Passo 5 – Gerar o código gRPC

Com o ambiente virtual ativo, na raiz do projeto:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. calculadora.proto
```

| Opção | Função |
|-------|--------|
| `-I.` | Diretório (`.` = pasta atual) onde o `protoc` procura arquivos `.proto` |
| `--python_out=.` | Gera `calculadora_pb2.py` (classes `OperacaoRequest` e `OperacaoResponse`) |
| `--grpc_python_out=.` | Gera `calculadora_pb2_grpc.py` (`CalculadoraStub`, `CalculadoraServicer` e `add_CalculadoraServicer_to_server`) |

✅ **Verificação:** a pasta deve conter agora `calculadora_pb2.py` e `calculadora_pb2_grpc.py`.

> ⚠️ Sempre que alterar o `calculadora.proto`, **rode este comando de novo**.

---

### Passo 6 – Implementar o servidor (`servidor.py`)

Crie o arquivo **`servidor.py`**:

```python
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
```

**Explicação:**

- **`CalculadoraServicer`**: herda da classe base gerada e **sobrescreve** cada método do contrato. Cada método recebe:
  - `request`: a mensagem `OperacaoRequest` já desserializada (`request.numero1`, `request.numero2`, `request.numero3`);
  - `context`: permite controlar a chamada (status de erro, metadados, cancelamento).
- **Semântica com três números (associatividade à esquerda):**

  | Operação | Fórmula |
  |----------|---------|
  | Soma | `a + b + c` |
  | Subtração | `(a − b) − c` |
  | Multiplicação | `a × b × c` |
  | Divisão | `(a ÷ b) ÷ c` |

- **`context.abort(...)`**: interrompe a chamada e devolve ao cliente um código de status gRPC (`INVALID_ARGUMENT`) com uma mensagem.
- **`grpc.server(ThreadPoolExecutor(max_workers=10))`**: servidor com *pool* de 10 threads, para atender vários clientes ao mesmo tempo.
- **`add_CalculadoraServicer_to_server`**: registra a implementação no servidor.
- **`add_insecure_port("[::]:50051")`**: escuta em todas as interfaces na porta 50051, **sem TLS** (adequado para fins didáticos).
- **`wait_for_termination()`**: mantém o servidor ativo até `Ctrl+C`.

---

### Passo 7 – Implementar o cliente (`cliente.py`)

Crie o arquivo **`cliente.py`**:

```python
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
```

**Explicação:**

- **`grpc.insecure_channel`**: abre o canal de comunicação com o servidor (sem TLS).
- **`CalculadoraStub`**: *proxy* gerado que expõe os métodos remotos como funções Python normais (`stub.Somar(...)`).
- **Dicionário `operacoes`**: liga a opção do menu ao método remoto, evitando uma cadeia de `if/elif`.
- **`ler_numero`**: valida a entrada e aceita vírgula decimal (`2,5` vira `2.5`).
- **`try/except grpc.RpcError`**: captura erros do servidor (como divisão por zero) e os mostra sem derrubar o cliente.

---

### Passo 8 – Criar o `.gitignore` (recomendado)

Crie o arquivo `.gitignore` com:

```
venv/
__pycache__/
*.pyc
```

---

### Passo 9 – Executar e testar

Siga a [seção 8](#8-como-executar-projeto-já-pronto) (dois terminais: um para o servidor, outro para o cliente) e faça os testes da [seção 12](#12-testes-manuais-sugeridos).

---

## 8. Como executar (projeto já pronto)

Use esta seção quando alguém clonar o repositório ou extrair o `.zip`.

### 8.1 Preparar o ambiente (uma única vez)

```bash
# 1. Clone o repositório (ou extraia o .zip)
git clone https://github.com/<seu-usuario>/calc-grpc.git
cd calc-grpc

# 2. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Gere o código gRPC (caso os arquivos *_pb2*.py não estejam no projeto)
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. calculadora.proto
```

### 8.2 Terminal 1 – iniciar o servidor

```bash
python3 servidor.py
```

Saída esperada:

```
Servidor gRPC da calculadora rodando na porta 50051...
```

> Deixe este terminal aberto. Para encerrar, use `Ctrl+C`.

### 8.3 Terminal 2 – iniciar o cliente

Abra **outro terminal**, entre na pasta, ative o ambiente virtual (`source venv/bin/activate`) e rode:

```bash
python3 cliente.py
```

---

## 9. Exemplo de execução

**Cliente:**

```
========== CALCULADORA gRPC ==========
1 - Soma            (a + b + c)
2 - Subtração       (a - b - c)
3 - Multiplicação   (a * b * c)
4 - Divisão         (a / b / c)
0 - Sair
======================================
Escolha uma opção: 1
Digite o primeiro número: 10
Digite o segundo número: 5
Digite o terceiro número: 2

>>> Soma: resultado = 17.0
```

**Servidor (log da chamada):**

```
[Somar] 10.0 + 5.0 + 2.0 = 17.0
```

### Resultados para `a = 100`, `b = 5`, `c = 2`

| Operação | Cálculo | Resultado |
|----------|---------|-----------|
| Soma | 100 + 5 + 2 | `107.0` |
| Subtração | (100 − 5) − 2 | `93.0` |
| Multiplicação | 100 × 5 × 2 | `1000.0` |
| Divisão | (100 ÷ 5) ÷ 2 | `10.0` |

