# SISTEMAS DISTRIBUÍDOS - Primeira Prática de Docker
## FRANCISCO DAGOBERTO SILVA DOS SANTOS - 554237
## CIÊNCIA DA COMPUTAÇÃO

# ARQUIVOS
### Arquivo app/app.py

```
from flask import Flask
import redis
import os

app = Flask(__name__)

# Nome do host do Redis
redis_host = os.getenv("REDIS_HOST", "localhost")

# Conexão com o Redis
r = redis.Redis(
    host=redis_host,
    port=6379,
    decode_responses=True
)

@app.route("/")
def home():
    # Incrementa o número de acessos
    acessos = r.incr("acessos")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Prática Docker</title>
    </head>
    <body>
        <h1>Olá, Docker!</h1>
        <p>Número de acessos: {acessos}</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)

```
| Nº | Código/Conceito | Descrição |
|---:|---|---|
| 1 | `Flask(__name__)` | Cria a aplicação web utilizando o framework Flask. |
| 2 | `os.getenv("REDIS_HOST", "localhost")` | Obtém o nome do host do Redis pela variável de ambiente `REDIS_HOST`. Caso ela não esteja definida, utiliza `localhost` como padrão. |
| 3 | `redis.Redis(...)` | Cria a conexão com o serviço Redis utilizando o host configurado, a porta `6379` e `decode_responses=True` para retornar respostas como strings. |
| 4 | `@app.route("/")` | Define a rota principal (`/`) da aplicação, acessada quando o usuário entra na página inicial. |
| 5 | `r.incr("acessos")` | Incrementa em 1 o contador `acessos` armazenado no Redis a cada acesso à rota principal. |
| 6 | `return f"""..."""` | Retorna uma página HTML com o título **Prática Docker**, a mensagem **Olá, Docker!** e o número de acessos. |
| 7 | `app.run(host="0.0.0.0", port=5050)` | Inicia o servidor Flask escutando em todas as interfaces de rede do container, na porta interna `5050`. |
| 8 | `if __name__ == "__main__":` | Garante que o servidor Flask seja iniciado somente quando o arquivo Python for executado diretamente. |


### Arquivo app/requirements.txt

```
Flask
redis
```



### Arquivo Dockerfile
```
# Imagem base Python 
FROM python:3.9-slim

# Diretório de trabalho dentro do container 
WORKDIR /app 

# Copiar dependências e instalá-las 
COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt 

# Copiar os arquivos da aplicação 
COPY . . 

# Expor a porta padrão do Flask 
EXPOSE 5050 

# Comando para iniciar a aplicação 
CMD ["python", "app.py"]
```

| Nº | Instrução | Descrição |
|---:|---|---|
| 1 | `FROM python:3.9-slim` | Define a imagem base do Python 3.9 em uma versão mais leve, utilizada para criar o container. |
| 2 | `WORKDIR /app` | Define `/app` como o diretório de trabalho dentro do container. |
| 3 | `COPY requirements.txt .` | Copia o arquivo `requirements.txt` do projeto para o diretório de trabalho do container. |
| 4 | `RUN pip install --no-cache-dir -r requirements.txt` | Instala as dependências Python listadas no arquivo `requirements.txt`, sem armazenar o cache do pip. |
| 5 | `COPY . .` | Copia os arquivos do diretório atual do projeto para o diretório de trabalho do container. |
| 6 | `EXPOSE 5050` | Documenta que a aplicação utiliza a porta `5050` dentro do container. |
| 7 | `CMD ["python", "app.py"]` | Define o comando executado quando o container é iniciado, executando o arquivo `app.py`. |

# Construção da imagem Docker
### NO Terminal, Na raiz do projeto

```
docker build -t primeira-pratica-app .
```

| Comando | Descrição |
|---|---|
| `docker build` | Cria uma imagem Docker a partir das instruções definidas no `Dockerfile`. |
| `-t primeira-pratica-app` | Define o nome da imagem como `primeira-pratica-app`. |
| `.` | Indica que o diretório atual será utilizado como contexto de construção, contendo os arquivos necessários para criar a imagem. |

# Confira se a imagem foi criada:
### No terminal
```
docker images
```

| Comando | Descrição |
|---|---|
| `docker images` | Lista as imagens Docker disponíveis localmente no computador. |

# Execute a aplicação utilizando a imagem criada

### No Terminal 

```
docker run -d --name app -p 5000:5050 primeira-pratica-app
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker run` | Cria e inicia um container a partir de uma imagem Docker. |
| `-d` | Executa o container em segundo plano (*detached mode*). |
| `--name app` | Define o nome do container como `app`. |
| `-p 5000:5000` | Mapeia a porta `5000` do computador para a porta `5000` do container. |
| `primeira-pratica-app` | Indica a imagem utilizada para criar o container. |


# Confira o container

### No Terminal
```
docker ps
```

# remover o container de teste antes de continuar:

### No Terminal

```
docker rm -f app
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker rm` | Remove um container Docker. |
| `-f` | Força a remoção do container, interrompendo-o caso esteja em execução. |
| `app` | Nome do container que será removido. |

# Execute um container Redis
Agora é precisa criar o serviço responsável por armazenar o contador.

### No Terminal
```
docker network create rede-pratica
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker network create` | Cria uma nova rede Docker para permitir a comunicação entre containers. |
| `rede-pratica` | Define o nome da rede que será criada. |


### Em seguida, executar:

### No Terminal
```
docker run -d `
  --name redis `
  --network rede-pratica `
  redis:7 `
  redis-server --appendonly yes
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker run` | Cria e inicia um container a partir de uma imagem Docker. |
| `-d` | Executa o container em segundo plano (*detached mode*). |
| `--name redis` | Define o nome do container como `redis`. |
| `--network rede-pratica` | Conecta o container à rede Docker `rede-pratica`, permitindo a comunicação com outros containers nessa rede. |
| `redis:7` | Especifica a imagem Redis na versão 7. |
| `redis-server --appendonly yes` | Inicia o servidor Redis com o AOF habilitado, registrando operações de escrita para ajudar na recuperação dos dados após reinicializações. |

# Conferir a execução
### No Terminal
```
docker ps
```

# Verifique se o Redis está respondendo:

### No Terminal
```
docker exec redis redis-cli PING
```
| Comando/Parâmetro | Descrição |
|---|---|
| `docker exec` | Executa um comando dentro de um container em execução. |
| `redis` | Identifica o nome do container no qual o comando será executado. |
| `redis-cli` | Abre a interface de linha de comando do Redis para enviar comandos ao servidor. |
| `PING` | Envia uma mensagem de teste ao Redis para verificar se ele está respondendo. |
#


## Questão 1: os serviços precisam se comunicar. Como fazer isso?
### A solução é colocar os dois containers na mesma rede Docker. Nessa rede, a aplicação poderá acessar o Redis usando o nome redis, sem precisar descobrir seu endereço IP.


# Configuração da comunicação entre Flask e Redis
### Executando a aplicação novamente, agora conectando-a à rede criada e informando o host correto:

### No Terminal 
```
docker run -d `
  --name app `
  --network rede-pratica `
  -p 5000:5050 `
  -e REDIS_HOST=redis `
  primeira-pratica-app
```
| Comando/Parâmetro | Descrição |
|---|---|
| `docker run` | Cria e inicia um container a partir de uma imagem Docker. |
| `-d` | Executa o container em segundo plano (*detached mode*). |
| `--name app` | Define o nome do container como `app`. |
| `--network rede-pratica` | Conecta o container à rede `rede-pratica`, permitindo a comunicação com o Redis. |
| `-p 5000:5050` | Mapeia a porta `5050` do container para a porta `5000` do computador. |
| `-e REDIS_HOST=redis` | Define a variável de ambiente `REDIS_HOST` com o valor `redis`, que é o nome do container Redis. |
| `primeira-pratica-app` | Especifica a imagem Docker utilizada para criar o container da aplicação Flask. |
# Abra o navegador em

### http://localhost:5000
#

## Questão 2: Por que utilizar o nome do serviço é mais adequado do que utilizar diretamente o IP do container? 

### Porque o IP de um container pode mudar quando ele é recriado. O nome do serviço permite que o Docker faça a resolução do endereço dentro da rede, tornando a configuração mais estável.


# Migrar a aplicação para Docker Compose
Em vez de executar vários comandos manualmente, vou descrever os serviços em um único arquivo **docker-compose.yml**.

# Primeiro, remover os containers de teste:
### No Terminal

```
docker rm -f app redis
```

```
docker network rm rede-pratica
```

# Agora criar o arquivo docker-compose.yml na raiz do projeto.

### arquivo app/docker-compose.yml

```
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5050"
    environment:
      REDIS_HOST: redis
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - rede-pratica

  redis:
    image: redis:7
    command: redis-server --appendonly yes
    volumes:
      - redis-dados:/data
    networks:
      - rede-pratica
    healthcheck:
      test: ["CMD", "redis-cli", "PING"]
      interval: 5s
      timeout: 3s
      retries: 5

networks:
  rede-pratica:
    driver: bridge

volumes:
  redis-dados:
```

| Nº | Instrução | Descrição |
|---:|---|---|
| 1 | `services:` | Define os serviços que serão executados no ambiente Docker Compose. |
| 2 | `app:` | Define o serviço da aplicação Flask. |
| 3 | `build:` | Indica que a imagem da aplicação será construída a partir de um Dockerfile. |
| 4 | `context: .` | Define o diretório atual como contexto de construção da imagem. |
| 5 | `dockerfile: Dockerfile` | Especifica o arquivo utilizado para construir a imagem da aplicação. |
| 6 | `ports: - "5000:5000"` | Publica a porta 5000 do container na porta 5000 do computador. |
| 7 | `environment:` | Define variáveis de ambiente utilizadas pelo serviço. |
| 8 | `REDIS_HOST: redis` | Informa à aplicação Flask que o host do Redis é `redis`, o nome do serviço no Compose. |
| 9 | `depends_on:` | Define dependências entre os serviços. |
| 10 | `condition: service_healthy` | Aguarda o Redis passar no healthcheck antes de iniciar o serviço dependente. |
| 11 | `networks:` | Define as redes às quais o serviço estará conectado. |
| 12 | `rede-pratica:` | Conecta o serviço à rede personalizada chamada `rede-pratica`. |
| 13 | `redis:` | Define o serviço responsável pelo banco de dados em memória Redis. |
| 14 | `image: redis:7` | Utiliza a imagem oficial do Redis na versão 7. |
| 15 | `command: redis-server --appendonly yes` | Inicia o Redis com o mecanismo AOF habilitado para registrar operações de escrita. |
| 16 | `volumes: - redis-dados:/data` | Associa um volume persistente ao diretório de dados do Redis. |
| 17 | `healthcheck:` | Define verificações periódicas para avaliar se o Redis está funcionando. |
| 18 | `test: ["CMD", "redis-cli", "PING"]` | Executa o comando `redis-cli PING` para verificar a resposta do Redis. |
| 19 | `interval: 5s` | Executa a verificação de saúde a cada 5 segundos. |
| 20 | `timeout: 3s` | Define 3 segundos como tempo máximo para cada verificação. |
| 21 | `retries: 5` | Define 5 tentativas consecutivas malsucedidas antes de marcar o serviço como não saudável. |
| 22 | `driver: bridge` | Define o driver de rede `bridge` para comunicação entre os containers. |
| 23 | `volumes: redis-dados:` | Declara o volume nomeado `redis-dados`, usado para persistir os dados do Redis. |

# Execute tudo com Docker Compose

# Passo 1 — Validar o arquivo
Será que o arquivo **docker-compose.yml** existe na pasta em que estamos ?

### No Terminal
```
docker compose config
```

| Comando/Parte | Descrição |
|---|---|
| `docker compose` | Executa operações relacionadas ao Docker Compose. |
| `config` | Valida e exibe a configuração final do arquivo `docker-compose.yml`, considerando a interpretação do Compose e as substituições aplicáveis. |


# Passo 2 — Construir a imagem e iniciar os serviços

### No Terminal
```
docker compose up -d --build
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker compose` | Gerencia os serviços definidos no arquivo `docker-compose.yml`. |
| `up` | Cria e inicia os containers dos serviços configurados. |
| `-d` | Executa os containers em segundo plano (*detached mode*). |
| `--build` | Constrói ou reconstrói as imagens antes de iniciar os serviços. |

# Passo 3 — Conferir os containers
### No Terminal
```
docker compose ps
```
| Comando/Parâmetro | Descrição |
|---|---|
| `docker compose` | Gerencia os serviços definidos no arquivo `docker-compose.yml`. |
| `ps` | Lista os containers associados ao projeto Docker Compose e mostra seus estados. |



# Passo 4 — Consultar os logs

# No Terminal
```
docker compose logs
```

# Passo 5 — Testar a aplicação
### Abra novamente:
### http://localhost:5000


# Teste a persistência dos dados
## O objetivo é verificar se o contador permanece salvo mesmo quando o container Redis é recriado.

# Passo 1 — Gerar alguns acessos
## Acessar a aplicação várias vezes até que o contador esteja, por exemplo, em 30


# Passo 2 — Confira o volume

### No Terminal

```
docker volume ls
```
| Comando/Parâmetro | Descrição |
|---|---|
| `docker volume` | Gerencia os volumes Docker utilizados para armazenar dados. |
| `ls` | Lista os volumes existentes no computador. |

# Passo 3 — Inspecione o volume

### No Terminal
```
docker volume inspect app_redis-dados
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker volume` | Gerencia os volumes do Docker. |
| `inspect` | Exibe informações detalhadas sobre um volume específico. |
| `app_redis-dados` | Nome do volume que será inspecionado. Esse nome precisa corresponder a um volume existente. |

# Passo 4 — Reinicie os serviços

```
docker compose down
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker compose` | Gerencia os serviços definidos no arquivo `docker-compose.yml`. |
| `down` | Interrompe e remove os containers e as redes criados pelo projeto Docker Compose. |
```
docker compose up -d
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker compose` | Gerencia os serviços definidos no arquivo `docker-compose.yml`. |
| `up` | Cria e inicia os containers dos serviços configurados. |
| `-d` | Executa os containers em segundo plano (*detached mode*), liberando o terminal para outros comandos. |

# Importante: não utilize docker compose down -v nesse teste, pois a opção -v remove os volumes nomeados criados pelo Compose.

# Passo 5 — Verifique o contador

### Acessar a aplicação novamente. Como o Redis utiliza AOF e está associado a um volume persistente, o valor anterior deverá ser recuperado.
### O contador só aumenta quando você acessa a rota /; apenas reiniciar os containers não deve incrementar o valor.

# Alteração na aplicação e reconstrução da imagem
## Abra app/app.py e alterei:

### arquivo app.py antes:
```
from flask import Flask
import redis
import os

app = Flask(__name__)

# Nome do host do Redis
redis_host = os.getenv("REDIS_HOST", "localhost")

# Conexão com o Redis
r = redis.Redis(
    host=redis_host,
    port=6379,
    decode_responses=True
)

@app.route("/")
def home():
    # Incrementa o número de acessos
    acessos = r.incr("acessos")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Prática Docker</title>
    </head>
    <body>
        <h1>Olá, Docker!</h1>
        <p>Número de acessos: {acessos}</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)

```


### arquivo app.py depois:
```
from flask import Flask
import redis
import os

app = Flask(__name__)

# Nome do host do Redis
redis_host = os.getenv("REDIS_HOST", "localhost")

# Conexão com o Redis
r = redis.Redis(
    host=redis_host,
    port=6379,
    decode_responses=True
)

@app.route("/")
def home():
    # Incrementa o número de acessos
    acessos = r.incr("acessos")

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Prática Docker</title>
    </head>
    <body>
        <h1>Olá, Docker! Prática de Sistemas Distribuídos</h1>
        <p>Número de acessos: {acessos}</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)

```

### Alteração feita no h1

### antes:
```
<h1>Olá, Docker!</h1>
```

### depois:
```
<h1>Olá, Docker! Prática de Sistemas Distribuídos</h1>
```

# Em seguida, executei:

### No Terminal: 
```
docker compose up -d --build
```

| Comando/Parâmetro | Descrição |
|---|---|
| `docker compose` | Gerencia os serviços definidos no arquivo `docker-compose.yml`. |
| `up` | Cria e inicia os containers dos serviços configurados. |
| `-d` | Executa os containers em segundo plano (*detached mode*). |
| `--build` | Constrói ou reconstrói as imagens antes de iniciar os serviços. |

### Abra novamente e ver a alteração feita:
### http://localhost:5000


# QUESTÕES DA PRÁTICA

## Questão 1: os serviços precisam se comunicar. Como fazer isso?
### A solução é colocar os dois containers na mesma rede Docker. Nessa rede, a aplicação poderá acessar o Redis usando o nome redis, sem precisar descobrir seu endereço IP.
#

## Questão 2: Por que utilizar o nome do serviço é mais adequado do que utilizar diretamente o IP do container? 

### Porque o IP de um container pode mudar quando ele é recriado. O nome do serviço permite que o Docker faça a resolução do endereço dentro da rede, tornando a configuração mais estável.
#

## Questão 3: por que foi necessário utilizar --build? 
### Porque o código-fonte foi alterado, mas a imagem existente não é atualizada automaticamente quando você modifica um arquivo no computador. O --build solicita a reconstrução da imagem com a nova versão do código.
#

## uestão 4: Qual é a função do Dockerfile na aplicação? 
### O Dockerfile descreve as instruções necessárias para construir a imagem da aplicação, incluindo a escolha da imagem base, a definição do diretório de trabalho, a cópia dos arquivos, a instalação das dependências e o comando de inicialização.
#

## Questão 5 — Qual é a função do Redis nessa arquitetura?
### O Redis é utilizado como um banco de dados em memória para armazenar e atualizar o contador de acessos da aplicação Flask.
#

## Questão 6 — Como o container Flask consegue encontrar o Redis sem conhecer seu endereço IP?
### Os dois serviços estão conectados à mesma rede Docker. O Docker fornece resolução de nomes nessa rede, permitindo que o Flask utilize o nome redis como endereço do serviço.

#
## Questão 7 — Qual é a função do volume utilizado pelo Redis?
### O volume mantém os dados do Redis fora do ciclo de vida do container. Assim, os dados podem continuar disponíveis mesmo quando o container é removido e recriado, desde que o volume seja preservado e a persistência esteja configurada corretamente.
#

## Questão 8 — Qual problema o Docker Compose resolve em relação à execução manual dos containers?
### O Docker Compose centraliza a configuração dos serviços, das redes, das portas, das variáveis de ambiente e dos volumes em um único arquivo. Isso simplifica a criação, a inicialização e o gerenciamento de aplicações compostas por vários containers.
#