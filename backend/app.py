"""Servidor web da fila virtual.

Uso (na pasta do projeto):
    python -m backend.app              -> conecta no broker MQTT e abre o dashboard
    python -m backend.app --sem-mqtt   -> so o dashboard (para testar sem rede)

Dashboard em http://localhost:5000
"""

import argparse
import sys

from flask import Flask, jsonify, render_template, request

from backend import config
from backend.armazenamento import carregar_eventos
from backend.estado_fila import EstadoFila
from backend.previsao import ARQ_HISTORICO, Previsor, carregar_historico, separar

app = Flask(__name__)

estado = EstadoFila()
previsor = Previsor()
metricas = {}
cliente = None


def preparar():
    global metricas

    if not ARQ_HISTORICO.exists():
        sys.exit("Historico nao encontrado. Rode antes: python simulador/gerar_historico.py")

    df = carregar_historico()
    treino, teste = separar(df)
    previsor.treinar(treino)
    resultado, _, _ = previsor.avaliar(teste)
    metricas = {
        "dados": "SIMULADOS (data/historico_simulado.csv)",
        "treino": len(treino),
        "teste": len(teste),
        "media_historica_min": round(previsor.media_historica, 2),
        "coeficientes": previsor.coeficientes(),
        **resultado,
    }
    print(f"[IA] modelo treinado | MAE media historica {resultado['convencional']['mae']} min"
          f" | MAE regressao {resultado['ia']['mae']} min")

    # recupera o que ja tinha sido gravado antes de reiniciar o servidor
    antigos = carregar_eventos()
    for e in antigos:
        estado.aplicar({**e, "sync": True}, agora=e["ts"])
    if antigos:
        print(f"[CSV] {len(antigos)} eventos carregados de data/eventos.csv")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/estado")
def api_estado():
    dados = estado.resumo(previsor)
    dados["mqtt_conectado"] = cliente.conectado if cliente else False
    return jsonify(dados)


@app.route("/api/eventos")
def api_eventos():
    n = request.args.get("n", default=20, type=int)
    n = max(1, min(n, 200))
    return jsonify(estado.ultimos_eventos(n))


@app.route("/api/metricas")
def api_metricas():
    with estado.lock:
        reais = {
            "atendimentos_medidos": len(estado.duracoes),
            "duracao_media_real_min": round(sum(estado.duracoes) / len(estado.duracoes), 2)
            if estado.duracoes else None,
        }
    return jsonify({**metricas, "prototipo": reais})


def main():
    global cliente

    parser = argparse.ArgumentParser(description="Backend da fila virtual")
    parser.add_argument("--sem-mqtt", action="store_true", help="nao conecta no broker")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    parser.add_argument("--porta", type=int, default=config.PORTA_WEB)
    args = parser.parse_args()

    sys.stdout.reconfigure(line_buffering=True)   # mostra os prints do MQTT na hora
    preparar()

    if not args.sem_mqtt:
        from backend.mqtt_cliente import ClienteMqtt
        cliente = ClienteMqtt(estado, previsor, broker=args.broker)
        cliente.iniciar()

    print(f"Dashboard: http://localhost:{args.porta}")
    app.run(host="0.0.0.0", port=args.porta, debug=False)


if __name__ == "__main__":
    main()
