# Firmware ESP32 — Fila Virtual

- Projeto no Wokwi: https://wokwi.com/projects/480520205989381121
- Placa: ESP32 DevKit V1 (simulada)
- Arquivos: `esp32_fila_virtual.ino` (código), `diagram.json` (circuito), `libraries.txt` (bibliotecas)
- Organização: o `loop()` (núcleo 1) cuida de botões, LCD e LEDs; a tarefa `tarefaRede` (FreeRTOS, núcleo 0) cuida de Wi-Fi, NTP e MQTT. Assim, uma reconexão lenta não trava os botões.

## Como rodar no Wokwi (pelo navegador, sem instalar nada)

1. Acesse https://wokwi.com/projects/new/esp32 e faça login (a conta é necessária para salvar e gerar o link).
2. Na aba `sketch.ino`, apague tudo e cole o conteúdo de `esp32_fila_virtual.ino`.
3. Na aba `diagram.json`, apague tudo e cole o conteúdo de `diagram.json`.
4. Na aba **Library Manager**, clique em **+** e adicione `PubSubClient`, `LiquidCrystal I2C` e `ArduinoJson`.
5. Clique em ▶ (a primeira compilação leva uns 30 a 60 s na fila gratuita).
6. Clique em **Save** e depois em **Share**, e coloque o link no topo deste arquivo e no README principal.

## Pinagem

| Componente | Pino |
|------------|------|
| Botão CHEGADA (verde) | GPIO 18 (INPUT_PULLUP) |
| Botão ATENDIDO (azul) | GPIO 19 (INPUT_PULLUP) |
| LED verde (operação ok) | GPIO 2 (resistor de 220 Ω) |
| LED vermelho (operação inválida) | GPIO 4 (resistor de 220 Ω) |
| LCD 16x2 I2C | SDA 21 / SCL 22 (endereço 0x27) |

## Comandos no Serial Monitor

| Tecla | Ação |
|-------|------|
| `c` | chegada (mesmo efeito do botão verde) |
| `a` | atendido (mesmo efeito do botão azul) |
| `l` | lista os eventos guardados na memória |
| `s` | status: chip, clock, flash, heap, `sizeof(Evento)`, tempo do loop, Wi-Fi/MQTT/NTP |

## MQTT

Broker: `broker.hivemq.com:1883`

| Tópico | Sentido | Exemplo |
|--------|---------|---------|
| `fiap1cc/569729-568938/fila/evento` | ESP32 → backend | `{"seq":3,"tipo":"CHEGADA","ts":1763000000,"sync":true,"fila":3,"concluidos":10,"origem":"WOKWI"}` |
| `fiap1cc/569729-568938/fila/status` | ESP32 → backend (a cada 10 s, retained) | `{"online":true,"fila":3,"concluidos":10,"heap":...,"rssi":-60,...}` |
| `fiap1cc/569729-568938/fila/previsao` | backend → ESP32 | `{"conv_min":12.5,"ia_min":10.8}` |

Para testar sem o backend, publique uma previsão manualmente em http://www.hivemq.com/demos/websocket-client/ no tópico `.../previsao`.

Tipos de evento: `CHEGADA`, `ATENDIDO`, `SAIDA_INVALIDA` (atendido com a fila vazia), `CHEGADA_REJEITADA` (fila cheia, 99).
