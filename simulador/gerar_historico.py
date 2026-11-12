"""Gera um historico SIMULADO de atendimentos para treinar e avaliar a previsao.

Simula um posto com 1 atendente funcionando das 8h as 17h por 30 dias.
As chegadas seguem um processo de Poisson (taxa muda conforme a hora) e a
duracao do atendimento muda conforme o periodo do dia (no almoco fica mais lento).

Uso: python simulador/gerar_historico.py
"""

import csv
import random
from pathlib import Path

SEED = 42
DIAS = 30
ABERTURA = 8
FECHAMENTO = 17

# pessoas por hora
TAXA_CHEGADA = {8: 7, 9: 9, 10: 9, 11: 8, 12: 6, 13: 7, 14: 9, 15: 8, 16: 6}

ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "historico_simulado.csv"


def duracao_media(hora):
    if hora < 12:
        return 5.5
    if hora < 14:
        return 7.5   # horario de almoco, atendimento mais lento
    return 6.0


def sortear_duracao(rng, hora):
    media = duracao_media(hora)
    return max(1.5, rng.gauss(media, media * 0.3))


def formatar_hora(minutos):
    h = int(minutos // 60)
    m = int(minutos % 60)
    s = int(round((minutos * 60) % 60)) % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def simular_dia(rng, dia):
    # gera as chegadas do dia (em minutos desde 00:00)
    chegadas = []
    t = ABERTURA * 60.0
    while True:
        taxa = TAXA_CHEGADA[int(t // 60)] / 60.0
        t += rng.expovariate(taxa)
        if t >= FECHAMENTO * 60:
            break
        chegadas.append(t)

    linhas = []
    fins = []          # horario em que cada atendimento terminou
    duracoes = []
    fim_anterior = 0.0

    for chegada in chegadas:
        inicio = max(chegada, fim_anterior)
        duracao = sortear_duracao(rng, inicio / 60)
        fim = inicio + duracao

        # quem ainda nao terminou quando essa pessoa chegou esta na frente dela
        a_frente = sum(1 for f in fins if f > chegada)

        # media dos ultimos 5 atendimentos ja concluidos
        concluidos = [d for d, f in zip(duracoes, fins) if f <= chegada][-5:]
        recente = sum(concluidos) / len(concluidos) if concluidos else 6.0

        linhas.append({
            "dia": dia,
            "chegada": formatar_hora(chegada),
            "hora_do_dia": round(chegada / 60, 3),
            "pessoas_a_frente": a_frente,
            "duracao_recente_min": round(recente, 2),
            "duracao_atendimento_min": round(duracao, 2),
            "espera_real_min": round(inicio - chegada, 2),
            "origem": "SIMULADO",
        })

        fins.append(fim)
        duracoes.append(duracao)
        fim_anterior = fim

    return linhas


def main():
    rng = random.Random(SEED)
    todas = []
    for dia in range(1, DIAS + 1):
        todas.extend(simular_dia(rng, dia))

    ARQUIVO.parent.mkdir(exist_ok=True)
    with open(ARQUIVO, "w", newline="", encoding="utf-8") as f:
        campos = ["id"] + list(todas[0].keys())
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for i, linha in enumerate(todas, start=1):
            w.writerow({"id": i, **linha})

    esperas = [l["espera_real_min"] for l in todas]
    print(f"{len(todas)} atendimentos simulados em {DIAS} dias -> {ARQUIVO}")
    print(f"espera media: {sum(esperas) / len(esperas):.1f} min | maior espera: {max(esperas):.1f} min")


if __name__ == "__main__":
    main()
