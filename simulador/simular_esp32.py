"""Simula o ESP32 mandando eventos por MQTT (plano B se o Wokwi nao estiver disponivel).

Segue as mesmas regras do firmware: fila nunca negativa e no maximo 99 pessoas.
Os eventos saem com origem=SIMULADOR para nao confundir com os do Wokwi.

Uso:
    python simulador/simular_esp32.py            -> modo manual (c = chegada, a = atendido, q = sair)
    python simulador/simular_esp32.py --auto 30  -> gera 30 eventos aleatorios
"""

import argparse
import json
import random
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config  # noqa: E402

FILA_MAX = 99


class EspSimulado:
    def __init__(self, broker):
        self.fila = 0
        self.concluidos = 0
        self.seq = 0
        self.cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                   client_id=f"esp32-simulado-{random.randint(0, 9999)}")
        self.cliente.will_set(config.TOPICO_STATUS, json.dumps({"online": False}), retain=True)
        self.cliente.on_message = self.ao_receber
        self.cliente.connect(broker, config.MQTT_PORTA, keepalive=30)
        self.cliente.subscribe(config.TOPICO_PREVISAO)
        self.cliente.loop_start()
        self.status()

    def ao_receber(self, cliente, userdata, msg):
        try:
            p = json.loads(msg.payload)
            print(f"   previsao recebida -> media: {p['conv_min']} min | IA: {p['ia_min']} min")
        except (ValueError, KeyError):
            print("   previsao invalida")

    def publicar(self, tipo):
        msg = {
            "seq": self.seq, "tipo": tipo, "ts": int(time.time()), "sync": True,
            "fila": self.fila, "concluidos": self.concluidos, "origem": "SIMULADOR",
        }
        self.cliente.publish(config.TOPICO_EVENTO, json.dumps(msg))
        self.seq += 1
        print(f"#{msg['seq']} {tipo} fila={self.fila} concluidos={self.concluidos}")

    def status(self):
        msg = {"online": True, "fila": self.fila, "concluidos": self.concluidos, "simulado": True}
        self.cliente.publish(config.TOPICO_STATUS, json.dumps(msg), retain=True)

    def chegada(self):
        if self.fila >= FILA_MAX:
            self.publicar("CHEGADA_REJEITADA")
            return
        self.fila += 1
        self.publicar("CHEGADA")

    def atendido(self):
        if self.fila == 0:
            self.publicar("SAIDA_INVALIDA")
            return
        self.fila -= 1
        self.concluidos += 1
        self.publicar("ATENDIDO")

    def desligar(self):
        self.cliente.publish(config.TOPICO_STATUS, json.dumps({"online": False}), retain=True)
        time.sleep(0.5)
        self.cliente.loop_stop()
        self.cliente.disconnect()


def modo_manual(esp):
    print("c = chegada | a = atendido | q = sair")
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "c":
            esp.chegada()
        elif cmd == "a":
            esp.atendido()
        elif cmd == "q":
            break
        else:
            print("comando invalido")
        esp.status()
        time.sleep(0.3)


def modo_auto(esp, quantidade, intervalo):
    for _ in range(quantidade):
        # mais chegadas que saidas no comeco, depois equilibra
        if esp.fila < 3 or random.random() < 0.55:
            esp.chegada()
        else:
            esp.atendido()
        esp.status()
        time.sleep(intervalo)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto", type=int, metavar="N", help="gera N eventos aleatorios")
    parser.add_argument("--intervalo", type=float, default=2.0, help="segundos entre eventos no modo auto")
    parser.add_argument("--broker", default=config.MQTT_BROKER)
    args = parser.parse_args()

    esp = EspSimulado(args.broker)
    try:
        if args.auto:
            modo_auto(esp, args.auto, args.intervalo)
            time.sleep(1)
        else:
            modo_manual(esp)
    except KeyboardInterrupt:
        pass
    finally:
        esp.desligar()


if __name__ == "__main__":
    main()
