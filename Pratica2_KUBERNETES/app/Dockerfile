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