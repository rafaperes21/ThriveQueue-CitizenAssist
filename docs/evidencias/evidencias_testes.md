# Evidências de Testes

Execução em 12/11/2026, ESP32 simulado no Wokwi ligado ao backend pelo broker `broker.hivemq.com`.
Os prints foram extraídos do vídeo de teste (30 s) gravado pela equipe.

## Testes mínimos do enunciado

| ID | Situação | Passos | Resultado | Evidência |
|----|----------|--------|-----------|-----------|
| T-01 | Chegada de novos cidadãos | Botão CHEGADA 3× com a fila vazia | ✅ LCD `Fila:03 At:000`; eventos #0, #1 e #2 (`CHEGADA`) com horário | [t01_tres_chegadas.png](prints/t01_tres_chegadas.png) |
| T-02 | Conclusão de atendimentos | Botão ATENDIDO 2× | ✅ LCD `Fila:01 At:002`; eventos #3 e #4 (`ATENDIDO`) | [t02_dois_atendimentos.png](prints/t02_dois_atendimentos.png) |
| T-03 | Saída com a fila vazia | ATENDIDO até zerar a fila e mais 1× | ✅ A fila continua em 0 (não fica negativa), o LED vermelho acende, o LCD mostra `FILA VAZIA!` e o evento #6 é `SAIDA_INVALIDA` | [t03_saida_fila_vazia.png](prints/t03_saida_fila_vazia.png) |
| T-04 | Atualização da estimativa | Observar o LCD a cada chegada | ✅ A previsão volta do backend a cada evento: 6/5 min → 12/10 min → 18/16 min (média/IA) | [t04_estimativa_atualizando.png](prints/t04_estimativa_atualizando.png) |

## Log do Serial Monitor (Wokwi)

```
[WIFI] conectando...
--- status ---
Chip ESP32-D0WDQ6-V3 | 2 nucleos | 240 MHz
Flash: 4194304 bytes | programa: 963760 bytes
Heap: 320692 total | 219660 livre | 220140 menor livre
sizeof(Evento) = 8 | buffer de eventos = 800 bytes
WiFi: off | MQTT: off | NTP: pendente
[WIFI] conectado, IP 10.10.0.2
[MQTT] conectando...
[MQTT] conectado
#0 CHEGADA | 12/11 18:25:04 | fila=1 | concluidos=0
[MQTT] previsao: media 6.0 min | IA 5.0 min
#1 CHEGADA | 12/11 18:25:06 | fila=2 | concluidos=0
[MQTT] previsao: media 12.1 min | IA 10.4 min
#2 CHEGADA | 12/11 18:25:07 | fila=3 | concluidos=0
[MQTT] previsao: media 18.1 min | IA 15.9 min
#3 ATENDIDO | 12/11 18:25:10 | fila=2 | concluidos=1
[MQTT] previsao: media 12.1 min | IA 10.4 min
#4 ATENDIDO | 12/11 18:25:11 | fila=1 | concluidos=2
[MQTT] previsao: media 6.0 min | IA 5.0 min
#5 ATENDIDO | 12/11 18:25:17 | fila=0 | concluidos=3
[MQTT] previsao: media 0.0 min | IA 0.0 min
#6 SAIDA_INVALIDA | 12/11 18:25:18 | fila=0 | concluidos=3
[MQTT] previsao: media 0.0 min | IA 0.0 min
```

(Trecho; o log completo inclui o boot do ESP32 e duas reconexões ao broker.)

## Observações

- **Ida e volta pela internet em até 1 s:** nos quadros do vídeo (a cada 0,5 s), a previsão nova aparece no LCD no quadro seguinte ao clique (botão → ESP32 → broker → backend → broker → ESP32).
- **Reconexões MQTT:** o log mostra o ESP32 reconectando ao broker público duas vezes. A fila continuou funcionando, e os eventos têm numeração sequencial (#0 a #6), sem lacunas. Isso entra no relatório como limitação de conectividade (broker público e rede simulada do Wokwi).
- **Previsão antiga retida:** logo após a 1ª chegada, o LCD mostrou por cerca de 0,5 s uma previsão que tinha ficado retida no broker de um teste anterior. Corrigido: o backend agora publica a previsão atual assim que conecta.

## Testes automáticos (pytest)

`python -m pytest -q` → **13 passed** (lógica da fila, pareamento FIFO, mensagens inválidas, online/offline, previsão).

## Teste do firmware no PC (mocks)

O firmware também foi compilado com g++ usando versões falsas das bibliotecas do ESP32 e passou nos cenários T-01 a T-04, debounce com repique, dois botões ao mesmo tempo, envio dos eventos acumulados offline e fila cheia (99).
