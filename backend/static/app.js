const tipos = {
  CHEGADA: { nome: "Chegada", icone: "i-entrada" },
  ATENDIDO: { nome: "Atendimento concluído", icone: "i-check" },
  SAIDA_INVALIDA: { nome: "Saída inválida", icone: "i-alerta", obs: "a fila já estava vazia" },
  CHEGADA_REJEITADA: { nome: "Chegada rejeitada", icone: "i-alerta", obs: "fila cheia" },
};

const MAX_ICONES = 12;
let ultimoResumo = "";

function minutos(valor) {
  if (valor === null || valor === undefined) return "–";
  if (valor < 1) return "< 1 min";
  return "~" + Math.round(valor) + " min";
}

function icone(id, classe) {
  return '<svg class="icone ' + (classe || "") + '" aria-hidden="true"><use href="#' + id + '"/></svg>';
}

function trocarNumero(id, texto) {
  const el = document.getElementById(id);
  if (el.textContent === String(texto)) return;
  el.textContent = texto;
  el.classList.remove("mudou");
  void el.offsetWidth;   // reinicia a animacao
  el.classList.add("mudou");
}

function chip(id, texto, ok) {
  const el = document.getElementById(id);
  el.querySelector("span").textContent = texto;
  el.className = "chip " + (ok ? "ok" : "erro");
}

function desenharFila(qtd) {
  const caixa = document.getElementById("fila-visual");
  let html = "";
  for (let i = 0; i < Math.min(qtd, MAX_ICONES); i++) html += icone("i-pessoa");
  if (qtd > MAX_ICONES) html += '<span class="mais">+' + (qtd - MAX_ICONES) + "</span>";
  caixa.innerHTML = html;
}

function desenharBarras(conv, ia) {
  const maior = Math.max(conv, ia, 1);
  document.getElementById("barra-ia").style.width = (ia / maior) * 100 + "%";
  document.getElementById("barra-conv").style.width = (conv / maior) * 100 + "%";
}

// uma frase so para o leitor de tela, em vez de varios numeros soltos
function atualizarResumo(d) {
  let texto;
  if (d.fila === 0) {
    texto = "Ninguém aguardando agora. " + d.concluidos + " atendimentos concluídos.";
  } else {
    const pessoas = d.fila === 1 ? "1 pessoa aguardando" : d.fila + " pessoas aguardando";
    texto = pessoas + ". Espera estimada de " + minutos(d.espera_ia_min).replace("~", "cerca de ") + ".";
  }
  if (texto !== ultimoResumo) {
    document.getElementById("resumo").textContent = texto;
    ultimoResumo = texto;
  }
}

async function atualizarEstado() {
  try {
    const r = await fetch("/api/estado");
    const d = await r.json();

    trocarNumero("fila", d.fila);
    trocarNumero("concluidos", d.concluidos);
    desenharFila(d.fila);

    if (d.fila === 0) {
      trocarNumero("espera-ia", "Sem espera");
      document.getElementById("valor-ia").textContent = "0 min";
      document.getElementById("espera-conv").textContent = "0 min";
      desenharBarras(0, 0);
    } else {
      trocarNumero("espera-ia", minutos(d.espera_ia_min));
      document.getElementById("valor-ia").textContent = minutos(d.espera_ia_min);
      document.getElementById("espera-conv").textContent = minutos(d.espera_convencional_min);
      desenharBarras(d.espera_convencional_min, d.espera_ia_min);
    }
    document.getElementById("duracao").textContent = d.duracao_recente_min.toFixed(1).replace(".", ",") + " min";
    atualizarResumo(d);

    const sinal = d.ultimo_sinal ? " · " + d.ultimo_sinal : "";
    chip("status-esp", "ESP32 " + (d.online ? "online" : "offline") + sinal, d.online);
    chip("status-mqtt", "MQTT " + (d.mqtt_conectado ? "conectado" : "desconectado"), d.mqtt_conectado);
  } catch (e) {
    chip("status-esp", "Servidor fora do ar", false);
  }
}

async function atualizarEventos() {
  try {
    const r = await fetch("/api/eventos?n=8");
    const lista = await r.json();
    if (lista.length === 0) return;

    const ol = document.getElementById("eventos");
    ol.innerHTML = "";
    for (const e of lista) {
      const t = tipos[e.tipo] || { nome: e.tipo, icone: "i-info" };
      const li = document.createElement("li");

      const caixaIcone = document.createElement("span");
      caixaIcone.className = "evento-icone " + e.tipo;
      caixaIcone.innerHTML = icone(t.icone);

      const texto = document.createElement("div");
      texto.className = "evento-texto";
      const titulo = document.createElement("strong");
      titulo.textContent = t.nome;
      const detalhe = document.createElement("span");
      detalhe.textContent = "Fila: " + e.fila + " · Concluídos: " + e.concluidos + (t.obs ? " · " + t.obs : "");
      texto.append(titulo, detalhe);

      const hora = document.createElement("time");
      hora.className = "evento-hora";
      hora.textContent = e.hora.split(" ")[1] || e.hora;

      li.append(caixaIcone, texto, hora);
      ol.appendChild(li);
    }
  } catch (e) {
    // tenta de novo na proxima rodada
  }
}

async function carregarMetricas() {
  try {
    const r = await fetch("/api/metricas");
    const m = await r.json();
    document.getElementById("media-hist").textContent = m.media_historica_min.toFixed(2).replace(".", ",") + " min";
    document.getElementById("n-dados").textContent = m.treino + " atendimentos de treino, " + m.teste + " de teste";

    const linhas = [["Média histórica", m.convencional, "media"], ["Regressão linear", m.ia, "ia"]];
    const maior = Math.max(m.convencional.mae, m.ia.mae);

    const erros = document.getElementById("erros");
    erros.innerHTML = "";
    const corpo = document.getElementById("metricas");
    corpo.innerHTML = "";

    for (const [nome, v, classe] of linhas) {
      const linha = document.createElement("div");
      linha.className = "barra-linha";
      linha.innerHTML =
        '<span class="barra-rotulo">' + (classe === "ia" ? "IA" : "Média") + "</span>" +
        '<span class="barra"><span class="barra-valor ' + classe + '" style="width:' + (v.mae / maior) * 100 + '%"></span></span>' +
        '<span class="barra-num">' + v.mae.toFixed(2).replace(".", ",") + " min</span>";
      linha.setAttribute("aria-hidden", "true");   // a tabela abaixo tem os mesmos valores
      erros.appendChild(linha);

      const tr = document.createElement("tr");
      [nome, v.mae + " min", v.rmse + " min", v.r2].forEach((valor) => {
        const td = document.createElement("td");
        td.textContent = String(valor).replace(".", ",");
        tr.appendChild(td);
      });
      corpo.appendChild(tr);
    }
  } catch (e) {
    document.getElementById("metricas").innerHTML = "<tr><td colspan='4'>Não foi possível carregar as métricas.</td></tr>";
  }
}

function atualizar() {
  atualizarEstado();
  atualizarEventos();
}

carregarMetricas();
atualizar();
setInterval(atualizar, 2000);
