"""Previsao do tempo de espera.

Duas formas de estimar:
  - convencional: pessoas na frente x duracao media historica do atendimento
  - IA (regressao linear): aprende com o historico usando
        pessoas_a_frente, carga (pessoas_a_frente x duracao_recente) e hora_do_dia

Rodando direto (python -m backend.previsao) treina com os dias 1-24, testa
com os dias 25-30 e salva a comparacao em docs/relatorio/.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

RAIZ = Path(__file__).resolve().parent.parent
ARQ_HISTORICO = RAIZ / "data" / "historico_simulado.csv"
PASTA_RELATORIO = RAIZ / "docs" / "relatorio"

COLUNAS = ["pessoas_a_frente", "carga", "hora_do_dia"]


def montar_x(pessoas, duracao_recente, hora):
    pessoas = np.asarray(pessoas, dtype=float)
    duracao_recente = np.asarray(duracao_recente, dtype=float)
    hora = np.asarray(hora, dtype=float)
    return np.column_stack([pessoas, pessoas * duracao_recente, hora])


class Previsor:
    def __init__(self):
        self.modelo = LinearRegression()
        self.media_historica = 6.0
        self.treinado = False

    def treinar(self, df):
        self.media_historica = float(df["duracao_atendimento_min"].mean())
        x = montar_x(df["pessoas_a_frente"], df["duracao_recente_min"], df["hora_do_dia"])
        self.modelo.fit(x, df["espera_real_min"])
        self.treinado = True

    def convencional(self, pessoas):
        return max(0.0, pessoas * self.media_historica)

    def ia(self, pessoas, duracao_recente, hora):
        if pessoas == 0:
            return 0.0
        x = montar_x([pessoas], [duracao_recente], [hora])
        return max(0.0, float(self.modelo.predict(x)[0]))

    def coeficientes(self):
        coef = dict(zip(COLUNAS, [round(float(c), 4) for c in self.modelo.coef_]))
        coef["intercepto"] = round(float(self.modelo.intercept_), 4)
        return coef

    def avaliar(self, df):
        real = df["espera_real_min"].to_numpy()
        conv = df["pessoas_a_frente"].to_numpy() * self.media_historica
        x = montar_x(df["pessoas_a_frente"], df["duracao_recente_min"], df["hora_do_dia"])
        ia = np.clip(self.modelo.predict(x), 0, None)

        resultado = {}
        for nome, prev in [("convencional", conv), ("ia", ia)]:
            resultado[nome] = {
                "mae": round(float(mean_absolute_error(real, prev)), 3),
                "rmse": round(float(np.sqrt(mean_squared_error(real, prev))), 3),
                "r2": round(float(r2_score(real, prev)), 3),
            }
        return resultado, conv, ia


def carregar_historico(caminho=ARQ_HISTORICO):
    return pd.read_csv(caminho)


def separar(df, ultimo_dia_treino=24):
    treino = df[df["dia"] <= ultimo_dia_treino]
    teste = df[df["dia"] > ultimo_dia_treino]
    return treino, teste


def gerar_relatorio():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = carregar_historico()
    treino, teste = separar(df)

    p = Previsor()
    p.treinar(treino)
    metricas, conv, ia = p.avaliar(teste)

    print(f"treino: {len(treino)} atendimentos | teste: {len(teste)} atendimentos (dados SIMULADOS)")
    print(f"duracao media historica: {p.media_historica:.2f} min")
    print("coeficientes da regressao:", p.coeficientes())
    print(f"{'metodo':<14}{'MAE':>8}{'RMSE':>8}{'R2':>8}")
    for nome, m in metricas.items():
        print(f"{nome:<14}{m['mae']:>8}{m['rmse']:>8}{m['r2']:>8}")

    PASTA_RELATORIO.mkdir(parents=True, exist_ok=True)
    tabela = pd.DataFrame(metricas).T
    tabela.index.name = "metodo"
    tabela.to_csv(PASTA_RELATORIO / "metricas_previsao.csv")

    real = teste["espera_real_min"].to_numpy()
    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.5))

    limite = max(real.max(), conv.max(), ia.max()) + 2
    eixos[0].scatter(real, conv, s=12, alpha=0.5, label=f"Média histórica (MAE {metricas['convencional']['mae']})")
    eixos[0].scatter(real, ia, s=12, alpha=0.5, label=f"Regressão linear (MAE {metricas['ia']['mae']})")
    eixos[0].plot([0, limite], [0, limite], "k--", lw=1, label="previsão perfeita")
    eixos[0].set_xlabel("Espera real (min)")
    eixos[0].set_ylabel("Espera prevista (min)")
    eixos[0].set_title("Previsto x real (dias de teste)")
    eixos[0].legend(fontsize=8)

    por_pessoas = teste.assign(erro_conv=np.abs(conv - real), erro_ia=np.abs(ia - real))
    por_pessoas = por_pessoas.groupby("pessoas_a_frente")[["erro_conv", "erro_ia"]].mean()
    largura = 0.4
    pos = np.arange(len(por_pessoas))
    eixos[1].bar(pos - largura / 2, por_pessoas["erro_conv"], largura, label="Média histórica")
    eixos[1].bar(pos + largura / 2, por_pessoas["erro_ia"], largura, label="Regressão linear")
    eixos[1].set_xticks(pos, por_pessoas.index)
    eixos[1].set_xlabel("Pessoas na frente")
    eixos[1].set_ylabel("Erro médio absoluto (min)")
    eixos[1].set_title("Erro por tamanho da fila")
    eixos[1].legend(fontsize=8)

    fig.suptitle("Comparação das estimativas de espera (dados simulados)")
    fig.tight_layout()
    fig.savefig(PASTA_RELATORIO / "comparacao_previsao.png", dpi=130)
    print(f"salvo em {PASTA_RELATORIO}")


if __name__ == "__main__":
    gerar_relatorio()
