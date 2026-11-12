# Diagramas

Os `.svg` são os arquivos-fonte (dá para editar no VS Code ou no navegador); os `.png` são as versões usadas no relatório (2400 px de largura).

| Diagrama | O que mostra |
|----------|--------------|
| [arquitetura_sistema](arquitetura_sistema.png) | Entradas, ESP32 (núcleos, SRAM, flash, Wi-Fi), saídas e o caminho pela internet até o dashboard (Etapa 1) |
| [memoria_esp32](memoria_esp32.png) | Hierarquia de memória e uso medido: flash, heap, pilha da tarefa de rede, `struct Evento` e buffer (Etapa 5) |
| [fluxo_evento](fluxo_evento.png) | Sequência de um evento, do botão ao dashboard, separando o que roda em cada núcleo |
