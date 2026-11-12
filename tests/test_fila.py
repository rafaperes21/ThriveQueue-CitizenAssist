from backend.estado_fila import EstadoFila, validar

T0 = 1_763_000_000   # um horario qualquer depois de 2020


def evento(tipo, fila, concluidos, ts, seq=0):
    return {"seq": seq, "tipo": tipo, "ts": ts, "sync": True, "fila": fila,
            "concluidos": concluidos, "origem": "TESTE"}


def test_chegadas_e_atendimentos():
    e = EstadoFila()
    e.aplicar(evento("CHEGADA", 1, 0, T0))
    e.aplicar(evento("CHEGADA", 2, 0, T0 + 60))
    e.aplicar(evento("ATENDIDO", 1, 1, T0 + 300))
    assert e.fila == 1
    assert e.concluidos == 1
    assert len(e.eventos) == 3


def test_pareamento_fifo():
    e = EstadoFila()
    e.aplicar(evento("CHEGADA", 1, 0, T0))
    e.aplicar(evento("CHEGADA", 2, 0, T0 + 60))
    e.aplicar(evento("ATENDIDO", 1, 1, T0 + 300))   # 1a pessoa: 5 min de atendimento, sem espera
    e.aplicar(evento("ATENDIDO", 0, 2, T0 + 660))   # 2a pessoa: comecou 300, terminou 660
    assert e.duracoes == [5.0, 6.0]
    assert e.esperas == [0.0, 4.0]                  # esperou de 60 ate 300


def test_saida_invalida_nao_muda_fila():
    e = EstadoFila()
    e.aplicar(evento("SAIDA_INVALIDA", 0, 0, T0))
    assert e.fila == 0
    assert e.duracoes == []
    assert e.eventos[-1]["tipo"] == "SAIDA_INVALIDA"


def test_mensagens_invalidas():
    agora = T0
    assert validar("texto", agora) is None
    assert validar(evento("PULAR", 1, 0, T0), agora) is None
    assert validar(evento("CHEGADA", -1, 0, T0), agora) is None
    assert validar(evento("CHEGADA", 100, 0, T0), agora) is None
    assert validar(evento("CHEGADA", "3", 0, T0), agora) is None
    assert validar({"tipo": "CHEGADA"}, agora) is None

    e = EstadoFila()
    assert e.aplicar({"tipo": "CHEGADA", "fila": -5, "concluidos": 0}) is None
    assert e.invalidas == 1
    assert e.fila == 0


def test_sem_ntp_usa_hora_do_servidor():
    msg = evento("CHEGADA", 1, 0, 42)
    msg["sync"] = False
    ev = validar(msg, T0)
    assert ev["ts"] == T0


def test_sincroniza_com_contador_do_esp32():
    # backend ligou com 3 pessoas ja na fila (perdeu as chegadas)
    e = EstadoFila()
    e.aplicar(evento("CHEGADA", 4, 10, T0))
    assert e.fila == 4
    assert len(e.chegadas) == 4
    e.aplicar(evento("ATENDIDO", 3, 11, T0 + 300))   # chegada desconhecida, nao mede
    assert e.duracoes == []
    assert e.concluidos == 11


def test_online_offline():
    e = EstadoFila()
    assert not e.online(T0)
    e.atualizar_status({"online": True}, agora=T0)
    assert e.online(T0 + 5)
    assert not e.online(T0 + 60)
    e.atualizar_status({"online": False}, agora=T0 + 61)
    assert not e.online(T0 + 62)
