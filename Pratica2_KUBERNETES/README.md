# Segunda Prática de Sistemas Distribuídos — Kubernetes

**Universidade Federal do Ceará (UFC) — Campus de Crateús**  
**Disciplina:** Sistemas Distribuídos  
**Professor:** Anderson Almada

## 1. Objetivo

Nesta prática, a aplicação Flask que contabiliza acessos utilizando Redis, desenvolvida na Primeira Prática, será implantada e gerenciada com Kubernetes em um cluster local Minikube.

Os objetivos são:

- executar várias instâncias da aplicação;
- distribuir requisições por meio de um Service;
- manter o número desejado de Pods;
- aumentar e diminuir a quantidade de réplicas;
- observar a recuperação após a exclusão de um Pod (*Self-Healing*);
- atualizar a aplicação gradualmente (*Rolling Update*);
- retornar a uma versão anterior (*Rollback*).

> **Pré-requisito:** ter a aplicação da Primeira Prática e seu `Dockerfile` funcionando. Esta prática reutiliza esses arquivos; não é necessário recriar a aplicação nem utilizar Docker Compose para executar o Kubernetes.

## 2. Arquitetura

```text
                     Navegador
                         |
                         v
               Service contador
                    (NodePort)
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
         Pod Flask   Pod Flask   Pod Flask
             |           |           |
             +-----------+-----------+
                         |
                  Service redis
                         |
                         v
                     Pod Redis
```

O Deployment da aplicação começa com três réplicas. O Redis começa com uma réplica. O Service `contador` disponibiliza a aplicação, enquanto o Service `redis` fornece um endereço estável para a comunicação interna.

## 3. Pré-requisitos

Verifique se Docker Desktop, Minikube e `kubectl` estão instalados.

No PowerShell, execute:

```powershell
docker --version
minikube version
kubectl version --client
```

Se algum comando não for reconhecido, instale ou configure a ferramenta correspondente antes de continuar.

## 4. Iniciar o Minikube

Inicie o cluster local:

```powershell
minikube start
```

Confira os nós do cluster:

```powershell
kubectl get nodes
```

O nó deverá ficar com o status `Ready`.

## 5. Preparar a imagem da aplicação

Abra o PowerShell no diretório que contém o `Dockerfile` e o código da aplicação Flask.

Exemplo de navegação — ajuste o caminho conforme a localização do seu projeto:

```powershell
cd "C:\caminho\para\seu\projeto"
```

Construa a imagem dentro do ambiente Minikube:

```powershell
minikube image build -t contador:1.0 .
```

Confira as imagens disponíveis:

```powershell
minikube image ls
```

No PowerShell, você pode filtrar o resultado assim:

```powershell
minikube image ls | Select-String contador
```

O Deployment utilizará a imagem `contador:1.0`.

> **Atenção à porta:** os manifestos desta prática utilizam a porta `5050` para a aplicação. Confira se o Flask e o `Dockerfile` da Primeira Prática estão configurados de acordo. Se a aplicação escutar em outra porta, ajuste o código e os manifestos de forma consistente.

## 6. Criar a pasta dos manifestos

Na raiz do projeto, crie a pasta `k8s`:

```powershell
New-Item -ItemType Directory -Force -Path k8s
```

Crie dentro dela os quatro arquivos:

```text
k8s/
├── app-deployment.yaml
├── redis-deployment.yaml
├── redis-service.yaml
└── app-service.yaml
```

## 7. Deployment da aplicação Flask

Crie o arquivo `k8s/app-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: contador-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: contador
  template:
    metadata:
      labels:
        app: contador
    spec:
      containers:
        - name: contador
          image: contador:1.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 5050
          env:
            - name: REDIS_HOST
              value: redis
```

**Explicação:**

- `kind: Deployment`: define o recurso que gerencia as réplicas da aplicação.
- `replicas: 3`: solicita três Pods da aplicação.
- `image: contador:1.0`: seleciona a imagem construída anteriormente.
- `containerPort: 5050`: documenta a porta utilizada pela aplicação.
- `REDIS_HOST: redis`: configura o endereço do serviço Redis.
- `app: contador`: identifica os Pods que serão selecionados pelo Service da aplicação.

## 8. Deployment do Redis

Crie `k8s/redis-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:latest
          ports:
            - containerPort: 6379
```

Esse manifesto cria um Deployment com uma réplica do Redis, utilizando a imagem `redis:latest` e a porta `6379`.

> **Observação:** este manifesto não configura volume persistente para o Redis. Portanto, não considere garantida a preservação dos dados caso o Pod Redis seja recriado.

## 9. Service do Redis

Crie `k8s/redis-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  type: ClusterIP
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
```

O Service `redis` fornece um endereço estável dentro do cluster e encaminha as conexões para os Pods que possuem a label `app: redis`.

## 10. Service da aplicação

Crie `k8s/app-service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: contador
spec:
  type: NodePort
  selector:
    app: contador
  ports:
    - port: 5050
      targetPort: 5050
```

O Service `contador` disponibiliza a aplicação por meio do tipo `NodePort`. Seu seletor `app: contador` identifica os Pods que podem receber as requisições.

## 11. Aplicar os manifestos

Execute na raiz do projeto, onde está a pasta `k8s`:

```powershell
kubectl apply -f k8s/
```

Verifique os Pods:

```powershell
kubectl get pods
```

Verifique os Deployments:

```powershell
kubectl get deployments
```

Verifique os Services:

```powershell
kubectl get services
```

### Resultado esperado

- três Pods da aplicação Flask;
- um Pod do Redis;
- dois Deployments;
- dois Services.

A inicialização pode levar alguns instantes. Para acompanhar os Pods continuamente:

```powershell
kubectl get pods -w
```

Pressione `Ctrl + C` para encerrar o acompanhamento.

Se algum Pod não iniciar, consulte:

```powershell
kubectl describe pods
kubectl logs deployment/contador-deployment
kubectl logs deployment/redis-deployment
```

## 12. Acessar a aplicação

Execute:

```powershell
minikube service contador --url
```

Copie a URL exibida e abra-a no navegador. A aplicação deverá apresentar a mensagem e o contador de acessos.

Atualize a página algumas vezes para verificar se o contador aumenta.

Se houver problemas, confira:

```powershell
kubectl get pods
kubectl get services
kubectl get endpoints
kubectl logs deployment/contador-deployment
```

## 13. Escalar a aplicação

### 13.1 Aumentar de três para cinco réplicas

```powershell
kubectl scale deployment contador-deployment --replicas=5
```

Confira o resultado:

```powershell
kubectl get pods
kubectl get deployments
```

Aguarde até que as cinco réplicas da aplicação estejam prontas.

### 13.2 Reduzir de cinco para duas réplicas

```powershell
kubectl scale deployment contador-deployment --replicas=2
```

Confira novamente:

```powershell
kubectl get pods
kubectl get deployments
```

O Deployment ajusta automaticamente a quantidade de Pods para corresponder ao número solicitado.

## 14. Testar o Self-Healing

O Deployment tenta manter o número desejado de réplicas. Para observar esse comportamento, exclua um Pod da aplicação.

Primeiro, liste os Pods:

```powershell
kubectl get pods
```

Copie o nome de um Pod da aplicação e execute o comando abaixo, substituindo `NOME_DO_POD` pelo nome real:

```powershell
kubectl delete pod NOME_DO_POD
```

Observe os Pods:

```powershell
kubectl get pods -w
```

O Pod excluído será removido, e o Deployment deverá criar outro para manter a quantidade desejada de réplicas. O novo Pod terá um nome diferente.

Pressione `Ctrl + C` para parar de acompanhar.

## 15. Fazer o Rolling Update

### 15.1 Alterar a mensagem da aplicação

Abra o arquivo da aplicação Flask e altere a mensagem exibida, por exemplo, para:

```text
Olá, Kubernetes!
```

Salve o arquivo.

### 15.2 Construir a nova imagem

No diretório que contém o `Dockerfile`, execute:

```powershell
minikube image build -t contador:2.0 .
```

Confira se a imagem aparece na lista:

```powershell
minikube image ls | Select-String contador
```

### 15.3 Atualizar o Deployment

Abra `k8s/app-deployment.yaml` e altere:

```yaml
image: contador:1.0
```

para:

```yaml
image: contador:2.0
```

Salve o arquivo e aplique a alteração:

```powershell
kubectl apply -f k8s/app-deployment.yaml
```

Acompanhe o processo:

```powershell
kubectl rollout status deployment/contador-deployment
```

Confira os Pods:

```powershell
kubectl get pods
```

Consulte o histórico:

```powershell
kubectl rollout history deployment/contador-deployment
```

Para consultar uma revisão específica, conforme o histórico disponível:

```powershell
kubectl rollout history deployment/contador-deployment --revision=2
```

Quando a atualização terminar, abra novamente a URL obtida com `minikube service contador --url` e confira a nova mensagem.

## 16. Fazer o Rollback

Para retornar à revisão anterior do Deployment, execute:

```powershell
kubectl rollout undo deployment/contador-deployment
```

Acompanhe o processo:

```powershell
kubectl rollout status deployment/contador-deployment
```

Confira a configuração do Deployment:

```powershell
kubectl describe deployment contador-deployment
```

Abra novamente a aplicação no navegador. A mensagem deverá voltar à versão anterior correspondente à revisão restaurada.

## 17. Comandos úteis para a demonstração

| Objetivo | Comando |
|---|---|
| Ver os nós | `kubectl get nodes` |
| Ver os Pods | `kubectl get pods` |
| Ver os Deployments | `kubectl get deployments` |
| Ver os Services | `kubectl get services` |
| Ver os detalhes dos Pods | `kubectl describe pods` |
| Ver logs da aplicação | `kubectl logs deployment/contador-deployment` |
| Ver logs do Redis | `kubectl logs deployment/redis-deployment` |
| Escalar o Deployment | `kubectl scale deployment contador-deployment --replicas=5` |
| Acompanhar atualização | `kubectl rollout status deployment/contador-deployment` |
| Consultar histórico | `kubectl rollout history deployment/contador-deployment` |
| Desfazer atualização | `kubectl rollout undo deployment/contador-deployment` |
| Acessar a aplicação | `minikube service contador --url` |

## 18. Respostas às questões da prática

### Questão 1 — O que representa o nó apresentado pelo comando `kubectl get nodes`?

O nó representa uma máquina do cluster Kubernetes que disponibiliza recursos para executar os Pods. No Minikube, normalmente é um nó local utilizado como ambiente de execução do cluster.

### Questão 2 — Por que a aplicação deve utilizar `redis` em `REDIS_HOST`, em vez do endereço IP de um Pod Redis?

Porque o IP de um Pod pode mudar quando ele é recriado. Utilizar o nome do Service `redis` fornece um ponto de acesso estável, e o Kubernetes encaminha as requisições aos Pods selecionados pelo serviço.

### Questão 3 — Por que a aplicação possui três réplicas enquanto o Redis possui apenas uma réplica nesta prática?

A aplicação web pode executar múltiplas instâncias para distribuir requisições e aumentar sua capacidade de atendimento. O Redis possui uma réplica nesta atividade para simplificar a arquitetura e o exercício.

### Questão 4 — Qual é a função do Service do Redis?

O Service do Redis fornece um endereço estável dentro do cluster e encaminha as requisições para os Pods que correspondem ao seu seletor. Assim, a aplicação não precisa conhecer o IP individual do Pod Redis.

### Questão 5 — Como o Service `contador` sabe quais Pods devem receber as requisições?

O Service utiliza o seletor `app: contador`. O Kubernetes identifica os Pods com essa label e os utiliza como destinos do serviço.

### Questão 6 — O que aconteceu com os Pods quando o número de réplicas foi alterado de três para cinco e depois para dois?

Ao aumentar para cinco, o Kubernetes criou Pods adicionais para atingir a quantidade solicitada. Ao reduzir para duas, removeu os Pods excedentes. O Deployment gerencia essa quantidade de acordo com o estado desejado.

### Questão 7 — O Pod removido foi simplesmente perdido? Explique o que aconteceu após sua exclusão.

O Pod excluído deixou de existir, mas o Deployment continuou tentando manter a quantidade desejada de réplicas. Por isso, o Kubernetes criou outro Pod para substituí-lo.

### Questão 8 — O que caracteriza um Rolling Update? Por que ele é útil em aplicações que precisam permanecer disponíveis durante uma atualização?

Rolling Update é a substituição gradual dos Pods da versão antiga pelos Pods da nova versão. Isso reduz a necessidade de interromper todas as instâncias ao mesmo tempo e pode minimizar a indisponibilidade durante uma atualização.

### Questão 9 — Qual é a função do comando `kubectl rollout undo`?

O comando desfaz uma atualização do Deployment, retornando a uma revisão anterior disponível no histórico. É útil quando uma nova versão apresenta problemas e é necessário restaurar uma configuração anterior.

## 19. Roteiro do vídeo de entrega

O vídeo deve mostrar:

1. A estrutura dos arquivos e os manifestos YAML.
2. O Minikube iniciado e o nó em estado `Ready`.
3. A aplicação funcionando no navegador.
4. Os Pods em execução.
5. Os Deployments e os Services.
6. A escalabilidade de três para cinco e depois para duas réplicas.
7. A exclusão de um Pod e sua substituição automática.
8. A construção da imagem `contador:2.0` e o Rolling Update.
9. O Rollback e a confirmação da versão restaurada.

## 20. Checklist final

- [ ] Minikube iniciado.
- [ ] Imagem `contador:1.0` construída.
- [ ] Quatro manifestos YAML criados.
- [ ] Três Pods Flask e um Pod Redis em execução.
- [ ] Dois Deployments e dois Services funcionando.
- [ ] Aplicação acessível pelo navegador.
- [ ] Escalabilidade de três para cinco e depois para duas réplicas testada.
- [ ] Self-Healing demonstrado.
- [ ] Imagem `contador:2.0` construída e Rolling Update testado.
- [ ] Rollback executado e verificado.
- [ ] Respostas às nove questões incluídas.
- [ ] Vídeo de demonstração gravado.

---

**Observação:** esta prática utiliza os manifestos solicitados no enunciado. O Deployment Redis apresentado não configura volume persistente, e o Service da aplicação não define uma porta `nodePort` fixa; o Minikube pode disponibilizar a aplicação por meio de `minikube service contador --url`.
