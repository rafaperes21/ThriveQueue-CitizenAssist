"""Guarda os eventos recebidos do ESP32 em data/eventos.csv."""

import csv
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ_EVENTOS = RAIZ / "data" / "eventos.csv"

CAMPOS = ["seq", "ts", "hora", "tipo", "fila", "concluidos", "origem"]


def salvar_evento(evento, arquivo=ARQ_EVENTOS):
    arquivo = Path(arquivo)
    novo = not arquivo.exists()
    arquivo.parent.mkdir(exist_ok=True)
    with open(arquivo, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        if novo:
            w.writeheader()
        w.writerow(evento)


def carregar_eventos(arquivo=ARQ_EVENTOS):
    arquivo = Path(arquivo)
    if not arquivo.exists():
        return []
    with open(arquivo, newline="", encoding="utf-8") as f:
        eventos = []
        for linha in csv.DictReader(f):
            try:
                linha["seq"] = int(linha["seq"]) if linha["seq"] else None
                linha["ts"] = float(linha["ts"])
                linha["fila"] = int(linha["fila"])
                linha["concluidos"] = int(linha["concluidos"])
            except (ValueError, KeyError):
                continue   # linha corrompida, pula
            eventos.append(linha)
        return eventos
