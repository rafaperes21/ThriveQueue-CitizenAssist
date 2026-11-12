import pandas as pd
import pytest

from backend.estado_fila import EstadoFila
from backend.previsao import Previsor, carregar_historico, separar


@pytest.fixture(scope="module")
def previsor_treinado():
    df = carregar_historico()
    treino, _ = separar(df)
    p = Previsor()
    p.treinar(treino)
    return p


def test_historico_e_simulado():
    df = carregar_historico()
    assert len(df) > 500
    assert (df["origem"] == "SIMULADO").all()


def test_convencional_e_pessoas_vezes_media():
    p = Previsor()
    p.treinar(pd.DataFrame({
        "pessoas_a_frente": [0, 1, 2, 3],
        "duracao_recente_min": [5, 5, 5, 5],
        "hora_do_dia": [9, 10, 11, 12],
        "duracao_atendimento_min": [4, 6, 5, 5],
        "espera_real_min": [0, 5, 10, 15],
    }))
    assert p.media_historica == 5
    assert p.convencional(0) == 0
    assert p.convencional(4) == 20


def test_ia_sem_fila_e_zero(previsor_treinado):
    assert previsor_treinado.ia(0, 6, 10) == 0


def test_ia_cresce_com_a_fila(previsor_treinado):
    p = previsor_treinado
    valores = [p.ia(n, 6, 10) for n in range(1, 8)]
    assert all(a < b for a, b in zip(valores, valores[1:]))
    assert all(v >= 0 for v in valores)


def test_ia_erra_menos_que_a_media(previsor_treinado):
    _, teste = separar(carregar_historico())
    metricas, _, _ = previsor_treinado.avaliar(teste)
    assert metricas["ia"]["mae"] < metricas["convencional"]["mae"]


def test_estimativa_muda_quando_a_fila_muda(previsor_treinado):
    e = EstadoFila()
    t0 = 1_763_000_000
    e.aplicar({"tipo": "CHEGADA", "fila": 2, "concluidos": 0, "ts": t0, "sync": True})
    conv1, ia1, _ = e.estimativas(previsor_treinado, agora=t0)
    e.aplicar({"tipo": "CHEGADA", "fila": 5, "concluidos": 0, "ts": t0 + 10, "sync": True})
    conv2, ia2, _ = e.estimativas(previsor_treinado, agora=t0 + 10)
    assert conv2 > conv1
    assert ia2 > ia1
