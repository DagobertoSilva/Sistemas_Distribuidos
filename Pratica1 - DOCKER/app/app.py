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
