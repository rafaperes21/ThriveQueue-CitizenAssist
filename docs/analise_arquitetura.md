# Análise da Arquitetura (Etapa 5) — medições

Valores lidos no Wokwi em 12/11/2026 com o comando `s` no Serial Monitor.

## Processador e memória

| Item | Valor medido | Observação |
|------|--------------|------------|
| Chip | ESP32-D0WDQ6-V3 | Xtensa LX6, 32 bits |
| Núcleos / clock | 2 / 240 MHz | |
| Flash | 4.194.304 B (4 MB) | memória não volátil, acessada por SPI |
| Tamanho do programa | 963.760 B (v1) | ~23% da flash; ~74% da partição de app padrão (1,25 MB = 1.310.720 B) |
| Heap total | 320.692 B | parte da SRAM de 520 KB disponível para alocação dinâmica |
| Heap livre (após iniciar Wi-Fi) | 219.660 B | ~68% livre; o Wi-Fi e a pilha TCP/IP consomem a maior parte do que é usado |
| Menor heap livre (após alguns minutos) | 206.400 B | caiu ~13 KB durante o uso (buffers de TCP/MQTT e do NTP); continuou estável |
| `sizeof(Evento)` | 8 B | 4 (timestamp) + 2 (concluídos) + 1 (tipo) + 1 (fila), sem padding |
| Buffer de eventos | 800 B (100 eventos) | ~0,25% do heap total |
| Pilha da tarefa de rede | 8.192 B reservados, 5.940 B nunca usados | a tarefa usa no máximo ~2,2 KB; daria para reduzir a reserva |

## Desempenho: antes e depois de separar os núcleos

**v1 (tudo no `loop()`, núcleo 1):** botões, LCD, Wi-Fi e MQTT no mesmo laço.

| Medida | Valor |
|--------|-------|
| Tempo médio do `loop()` | 145 µs |
| **Tempo máximo do `loop()`** | **4.373.871 µs (4,4 s)** |

O `mqtt.connect()` é bloqueante: numa reconexão ao broker (DNS + TCP + handshake MQTT) o laço ficou parado 4,4 s. Nesse tempo os botões não são lidos (leitura por polling), então um clique curto se perderia.

**v2 (rede numa tarefa FreeRTOS no núcleo 0):** o `loop()` (núcleo 1) só cuida de botões, LCD e LEDs. A tarefa `tarefaRede` (núcleo 0, o mesmo da pilha Wi-Fi do ESP32) faz Wi-Fi, NTP e MQTT. O buffer de eventos é compartilhado e protegido por um mutex (`xSemaphoreCreateMutex`).

| Medida | Valor |
|--------|-------|
| Tempo médio do `loop()` | 119 µs |
| Tempo máximo do `loop()` | 100.517 µs (0,1 s) — é o próprio comando `s` imprimindo ~600 caracteres a 115200 baud (~52 ms na UART) |
| Tempo máximo de um ciclo da tarefa de rede | 1.017.856 µs (1,0 s) — a conexão ao broker, agora fora do laço dos botões |

Resultado: a demora da rede continua existindo, mas não afeta mais a entrada nem o display.

## Comunicação

| Item | Valor |
|------|-------|
| Latência botão → LCD com previsão | ≤ 1 s, estimada no vídeo com quadros a cada 0,5 s (ida e volta pelo broker) |
| Reconexões MQTT observadas (v1) | 2 em ~1 min. Causa provável: outra simulação de teste com o mesmo *client ID* conectada ao broker (dois clientes com o mesmo ID se derrubam). Na v2 o ID é sorteado a cada conexão |

## Pendências

- [ ] Opcional: medir a latência botão → dashboard (10 cliques, cronômetro) para a tabela de desempenho.
