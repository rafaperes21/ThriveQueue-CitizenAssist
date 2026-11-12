"""Cliente MQTT do backend: recebe os eventos do ESP32 e devolve a previsao."""

import json
import random

import paho.mqtt.client as mqtt

from backend import config
from backend.armazenamento import salvar_evento


class ClienteMqtt:
    def __init__(self, estado, previsor, broker=config.MQTT_BROKER, porta=config.MQTT_PORTA):
        self.estado = estado
        self.previsor = previsor
        self.broker = broker
        self.porta = porta
        self.conectado = False

        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id=f"backend-fila-{random.randint(0, 99999)}")
        self.cliente.on_connect = self.ao_conectar
        self.cliente.on_disconnect = self.ao_desconectar
        self.cliente.on_message = self.ao_receber
        self.cliente.reconnect_delay_set(min_delay=1, max_delay=10)

    def iniciar(self):
        print(f"[MQTT] conectando em {self.broker}:{self.porta}")
        self.cliente.connect_async(self.broker, self.porta, keepalive=30)
        self.cliente.loop_start()

    def parar(self):
        self.cliente.loop_stop()
        self.cliente.disconnect()

    def ao_conectar(self, cliente, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[MQTT] falha ao conectar: {reason_code}")
            return
        self.conectado = True
        print("[MQTT] conectado")
        cliente.subscribe([(config.TOPICO_EVENTO, 0), (config.TOPICO_STATUS, 0)])
        # sobrescreve a previsao que ficou retida no broker de uma execucao anterior
        self.publicar_previsao()

    def ao_desconectar(self, cliente, userdata, flags, reason_code, properties):
        self.conectado = False
        print(f"[MQTT] desconectado ({reason_code})")

    def ao_receber(self, cliente, userdata, msg):
        try:
            dados = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            print(f"[MQTT] mensagem que nao e JSON em {msg.topic}, ignorada")
            self.estado.invalidas += 1
            return

        if msg.topic == config.TOPICO_STATUS:
            self.estado.atualizar_status(dados)
            return

        evento = self.estado.aplicar(dados)
        if evento is None:
            print(f"[MQTT] evento invalido ignorado: {dados}")
            return

        salvar_evento(evento)
        print(f"[EVENTO] {evento['hora']} {evento['tipo']} fila={evento['fila']} concluidos={evento['concluidos']}")
        self.publicar_previsao()

    def publicar_previsao(self):
        with self.estado.lock:
            conv, ia, _ = self.estado.estimativas(self.previsor)
        msg = json.dumps({"conv_min": conv, "ia_min": ia})
        self.cliente.publish(config.TOPICO_PREVISAO, msg, retain=True)
