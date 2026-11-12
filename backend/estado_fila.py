"""Estado da fila no backend.

O ESP32 e quem manda no contador (ele valida os botoes). Aqui a gente so
acompanha: guarda os eventos, sincroniza fila/concluidos com o que veio na
mensagem e faz o pareamento FIFO chegada -> atendimento para descobrir
quanto tempo cada atendimento durou de verdade.
"""

import threading
import time
from collections import deque
from datetime import datetime

TIPOS = {"CHEGADA", "ATENDIDO", "SAIDA_INVALIDA", "CHEGADA_REJEITADA"}
FILA_MAX = 99
TEMPO_OFFLINE = 30   # segundos sem mensagem = offline


def hora_do_dia(ts):
    d = datetime.fromtimestamp(ts)
    return d.hour + d.minute / 60


def validar(dados, agora):
    """Confere a mensagem do ESP32. Retorna o evento arrumado ou None se for invalida."""
    if not isinstance(dados, dict):
        return None

    tipo = dados.get("tipo")
    fila = dados.get("fila")
    concluidos = dados.get("concluidos")

    if tipo not in TIPOS:
        return None
    if not isinstance(fila, int) or isinstance(fila, bool) or not 0 <= fila <= FILA_MAX:
        return None
    if not isinstance(concluidos, int) or isinstance(concluidos, bool) or concluidos < 0:
        return None

    # se o ESP32 ainda nao pegou a hora pelo NTP, usa a hora que a mensagem chegou
    ts = dados.get("ts")
    if not dados.get("sync") or not isinstance(ts, (int, float)) or ts < 1_600_000_000:
        ts = agora

    seq = dados.get("seq")
    return {
        "seq": seq if isinstance(seq, int) else None,
        "ts": float(ts),
        "hora": datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S"),
        "tipo": tipo,
        "fila": fila,
        "concluidos": concluidos,
        "origem": str(dados.get("origem", "?"))[:20],
    }


class EstadoFila:
    def __init__(self):
        self.lock = threading.Lock()
        self.fila = 0
        self.concluidos = 0
        self.eventos = deque(maxlen=200)
        self.chegadas = deque()     # horario de chegada de quem esta na fila
        self.duracoes = []          # duracao real dos atendimentos (min)
        self.esperas = []           # espera real de cada pessoa (min)
        self.ultimo_fim = None
        self.ultimo_sinal = None
        self.status_esp = {}
        self.invalidas = 0

    def aplicar(self, dados, agora=None):
        agora = agora or time.time()
        evento = validar(dados, agora)

        with self.lock:
            if evento is None:
                self.invalidas += 1
                return None

            if evento["tipo"] == "CHEGADA":
                self.chegadas.append(evento["ts"])
            elif evento["tipo"] == "ATENDIDO":
                self._parear(evento["ts"])

            self.fila = evento["fila"]
            self.concluidos = evento["concluidos"]
            self._acertar_chegadas()

            self.eventos.append(evento)
            self.ultimo_sinal = agora
            return evento

    def _parear(self, ts_fim):
        if not self.chegadas:
            return
        chegada = self.chegadas.popleft()
        if chegada is None:      # pessoa que entrou antes do backend ligar
            self.ultimo_fim = ts_fim
            return

        inicio = max(chegada, self.ultimo_fim or chegada)
        duracao = (ts_fim - inicio) / 60
        espera = (inicio - chegada) / 60
        # menos de 30 s nao e um atendimento de verdade (clique de teste)
        if 0.5 <= duracao < 120:
            self.duracoes.append(duracao)
            self.esperas.append(espera)
        self.ultimo_fim = ts_fim

    def _acertar_chegadas(self):
        # se perdeu alguma mensagem, deixa a lista do mesmo tamanho da fila do ESP32
        while len(self.chegadas) > self.fila:
            self.chegadas.popleft()
        while len(self.chegadas) < self.fila:
            self.chegadas.appendleft(None)
        if self.fila == 0:
            self.ultimo_fim = None

    def atualizar_status(self, dados, agora=None):
        if not isinstance(dados, dict):
            return
        with self.lock:
            self.status_esp = dados
            self.ultimo_sinal = agora or time.time()

    def online(self, agora=None):
        agora = agora or time.time()
        if self.ultimo_sinal is None:
            return False
        if self.status_esp.get("online") is False:
            return False
        return agora - self.ultimo_sinal < TEMPO_OFFLINE

    def duracao_recente(self):
        ultimas = self.duracoes[-5:]
        if len(ultimas) < 3:
            return None
        return sum(ultimas) / len(ultimas)

    def estimativas(self, previsor, agora=None):
        agora = agora or time.time()
        recente = self.duracao_recente() or previsor.media_historica
        conv = previsor.convencional(self.fila)
        ia = previsor.ia(self.fila, recente, hora_do_dia(agora))
        return round(conv, 1), round(ia, 1), round(recente, 2)

    def resumo(self, previsor, agora=None):
        agora = agora or time.time()
        with self.lock:
            conv, ia, recente = self.estimativas(previsor, agora)
            return {
                "fila": self.fila,
                "concluidos": self.concluidos,
                "espera_convencional_min": conv,
                "espera_ia_min": ia,
                "duracao_recente_min": recente,
                "online": self.online(agora),
                "ultimo_sinal": datetime.fromtimestamp(self.ultimo_sinal).strftime("%H:%M:%S")
                if self.ultimo_sinal else None,
                "esp32": self.status_esp,
                "atendimentos_medidos": len(self.duracoes),
                "mensagens_invalidas": self.invalidas,
            }

    def ultimos_eventos(self, n=20):
        with self.lock:
            return list(self.eventos)[-n:][::-1]
