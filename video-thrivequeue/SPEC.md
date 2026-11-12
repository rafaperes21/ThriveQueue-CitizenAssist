# SPEC — vídeo ThriveQueue (edição das gravações)

Fonte: 6 gravações de tela com narração (`videos(temp-folder)`), uma por bloco de `docs/roteiro_video.md`.
Saída: 1920×1080, 30 fps, **284,4 s (4:44)**, limite do enunciado 5:00.

## Cortes (tempo da mídia → tempo global)

| Clip | Fonte | Entrada | Saída | Global |
|---|---|---|---|---|
| Abertura (cartão) | — | — | — | 0,0 – 4,0 |
| b1 Problema | bloco1 | 2,9 | 32,6 | 4,0 – 33,7 |
| b2 Arquitetura | bloco2 | 6,0 | 66,0 | 33,7 – 93,7 |
| b3a Testes 1 | bloco3 | 10,3 | 34,6 | 93,7 – 118,0 |
| b3b Testes 2–4 | bloco3 | 38,9 | 97,1 | 118,0 – 176,2 |
| Replay T1 (mudo, 1,5×) | bloco3 | 13,2 | — | 166,1 – 174,6 |
| b4 Previsão | bloco4 | 1,2 | 37,6 | 176,2 – 212,6 |
| b5 Análise | bloco5 | 5,1 | 57,0 | 212,6 – 264,5 |
| b6 Encerramento | bloco6 | 1,0 | 14,9 | 264,5 – 278,4 |
| Cartão final | — | — | — | 278,4 – 284,4 |

Cortes tiram a janela do OBS e silêncios de borda; o corte interno do bloco 3 (34,6→38,9) cai dentro de um silêncio de 5,4 s.
O teste 4 foi narrado sem nova chegada na tela: o replay do teste 1 (marcado como replay) mostra o LCD indo de 6 → 12 → 18 min sincronizado com as palavras "6, 12, 18" (90,6 / 91,5 / 92,0 s na mídia).

## Câmera
- Recorte base das gravações de navegador: escala 1,187, centro (960, 575) — esconde abas e barra de tarefas.
- Movimentos: 0,8 s, `power2.inOut`, começando 0,2 s antes da palavra que nomeia a região. Escala máx. 2,8.

## Visual
- Cores do dashboard: verde `#047857`, verde-escuro `#065f46`, petróleo `#0e7490`, solar `#f59e0b`, tinta `#0b2e24`, fundo claro `#f3faf6`.
- Fonte: Inter (400/700/900, inclusa).
- Etiquetas de capítulo: cartão branco com aba verde, canto inferior esquerdo (x 96, base 96), 4,5 s; entrada 0,55 s por recorte, saída 0,35 s.
- Sobreposições de dados escurecem a gravação com véu `rgba(4,20,15,.74)`.

## Áudio
- Narração original, normalizada para −16 LUFS; fade de 0,15 s na entrada e 0,2 s na saída de cada corte.
- Sem música (pode ser adicionada depois).
