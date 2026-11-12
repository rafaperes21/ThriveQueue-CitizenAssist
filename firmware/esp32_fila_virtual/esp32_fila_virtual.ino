// Fila Virtual - Citizen Assist AI
// GS 2026.2 - Computer Organization and Architecture (1CC-FEV)
// Rafael Marinucci Peres (RM 569729) e David dos Reis Cardoso (RM 568938)
//
// Nucleo 1 (loop): botoes, LCD e LEDs
// Nucleo 0 (tarefaRede): Wi-Fi, NTP e MQTT
// Assim, se a conexao travar, os botoes continuam respondendo.
//
// Comandos no Serial Monitor: c = chegada, a = atendido, l = lista eventos, s = status

#include <WiFi.h>
#include <PubSubClient.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include <time.h>

#define BTN_CHEGADA   18
#define BTN_ATENDIDO  19
#define LED_VERDE      2
#define LED_VERMELHO   4

#define FILA_MAX       99
#define MAX_EVENTOS   100
#define DEBOUNCE_MS    50

const char* ssid = "Wokwi-GUEST";
const char* senha = "";

const char* broker = "broker.hivemq.com";
const int porta = 1883;
const char* topicoEvento = "fiap1cc/569729-568938/fila/evento";
const char* topicoStatus = "fiap1cc/569729-568938/fila/status";
const char* topicoPrevisao = "fiap1cc/569729-568938/fila/previsao";

enum TipoEvento { CHEGADA, ATENDIDO, SAIDA_INVALIDA, CHEGADA_REJEITADA };
const char* nomeEvento[] = {"CHEGADA", "ATENDIDO", "SAIDA_INVALIDA", "CHEGADA_REJEITADA"};

// 8 bytes por evento (4 + 2 + 1 + 1), sem padding
struct Evento {
  uint32_t hora;        // epoch; se for pequeno e porque o NTP ainda nao sincronizou (segundos desde o boot)
  uint16_t concluidos;
  uint8_t tipo;
  uint8_t fila;
};

Evento eventos[MAX_EVENTOS];   // buffer circular, compartilhado entre os dois nucleos
uint32_t totalEventos = 0;
uint32_t enviados = 0;
SemaphoreHandle_t travaEventos;  // mutex pra um nucleo nao ler o buffer enquanto o outro escreve

struct Botao {
  int pino;
  bool estado;
  bool leituraAnterior;
  unsigned long ultimaMudanca;
};

Botao btnChegada = {BTN_CHEGADA, HIGH, HIGH, 0};
Botao btnAtendido = {BTN_ATENDIDO, HIGH, HIGH, 0};

int fila = 0;
int concluidos = 0;

volatile bool temPrevisao = false;
volatile float esperaConv = 0;
volatile float esperaIA = 0;

LiquidCrystal_I2C lcd(0x27, 16, 2);
WiFiClient espClient;
PubSubClient mqtt(espClient);
char clientId[32];
TaskHandle_t tarefaRedeHandle;

unsigned long fimAviso = 0;
unsigned long fimLedVerde = 0;
unsigned long fimLedVermelho = 0;
char aviso[17] = "";
volatile bool atualizarTela = true;
volatile bool wifiConectado = false;
volatile bool mqttConectado = false;

// medicoes pro relatorio
unsigned long tempoLoop = 0;
unsigned long tempoLoopMax = 0;
volatile unsigned long tempoRedeMax = 0;
uint32_t menorHeap = 0;


uint32_t horaAtual() {
  time_t t = time(nullptr);
  if (t > 1600000000) return t;
  return millis() / 1000;
}

bool horaValida(uint32_t t) {
  return t > 1600000000;
}

void formatarHora(uint32_t t, char* buf, int tam) {
  if (!horaValida(t)) {
    snprintf(buf, tam, "boot+%lus", (unsigned long)t);
    return;
  }
  time_t tt = t;
  struct tm info;
  localtime_r(&tt, &info);
  strftime(buf, tam, "%d/%m %H:%M:%S", &info);
}

void mostrarAviso(const char* msg) {
  strncpy(aviso, msg, 16);
  aviso[16] = '\0';
  fimAviso = millis() + 1500;
  atualizarTela = true;
}

void piscarVerde() {
  digitalWrite(LED_VERDE, HIGH);
  fimLedVerde = millis() + 150;
}

void acenderVermelho() {
  digitalWrite(LED_VERMELHO, HIGH);
  fimLedVermelho = millis() + 1500;
}

void escreverLinha(int linha, const char* texto) {
  char buf[17];
  snprintf(buf, sizeof(buf), "%-16s", texto);
  lcd.setCursor(0, linha);
  lcd.print(buf);
}

void desenharTela() {
  atualizarTela = false;

  char linha[17];
  snprintf(linha, sizeof(linha), "Fila:%02d  At:%03d", fila, concluidos % 1000);
  escreverLinha(0, linha);

  if (millis() < fimAviso) {
    escreverLinha(1, aviso);
  } else if (fila == 0) {
    escreverLinha(1, "Sem espera");
  } else if (temPrevisao) {
    snprintf(linha, sizeof(linha), "Esp~%dm IA~%dm", (int)(esperaConv + 0.5), (int)(esperaIA + 0.5));
    escreverLinha(1, linha);
  } else if (!wifiConectado) {
    escreverLinha(1, "Wi-Fi offline");
  } else if (!mqttConectado) {
    escreverLinha(1, "MQTT offline");
  } else {
    escreverLinha(1, "Calculando...");
  }
}

void apagarLeds() {
  unsigned long agora = millis();
  if (fimLedVerde && agora >= fimLedVerde) {
    digitalWrite(LED_VERDE, LOW);
    fimLedVerde = 0;
  }
  if (fimLedVermelho && agora >= fimLedVermelho) {
    digitalWrite(LED_VERMELHO, LOW);
    fimLedVermelho = 0;
  }
  if (fimAviso && agora >= fimAviso) {
    fimAviso = 0;
    atualizarTela = true;
  }
}


// ---------- nucleo 1: fila, botoes e serial ----------

void registrar(TipoEvento tipo) {
  xSemaphoreTake(travaEventos, portMAX_DELAY);
  uint32_t seq = totalEventos;
  Evento& e = eventos[seq % MAX_EVENTOS];
  e.hora = horaAtual();
  e.tipo = tipo;
  e.fila = fila;
  e.concluidos = concluidos;
  totalEventos++;
  xSemaphoreGive(travaEventos);

  char hora[20];
  formatarHora(e.hora, hora, sizeof(hora));
  Serial.printf("#%lu %s | %s | fila=%d | concluidos=%d\n",
                (unsigned long)seq, nomeEvento[tipo], hora, fila, concluidos);
  atualizarTela = true;
}

void chegada() {
  if (fila >= FILA_MAX) {
    registrar(CHEGADA_REJEITADA);
    acenderVermelho();
    mostrarAviso("FILA CHEIA!");
    return;
  }
  fila++;
  piscarVerde();
  registrar(CHEGADA);
}

void atendido() {
  // nao deixa a fila ficar negativa
  if (fila == 0) {
    registrar(SAIDA_INVALIDA);
    acenderVermelho();
    mostrarAviso("FILA VAZIA!");
    return;
  }
  fila--;
  concluidos++;
  piscarVerde();
  registrar(ATENDIDO);
}

// retorna true so no momento em que o botao e apertado (depois do debounce)
bool apertou(Botao& b) {
  bool leitura = digitalRead(b.pino);

  if (leitura != b.leituraAnterior) {
    b.leituraAnterior = leitura;
    b.ultimaMudanca = millis();
  }

  if (millis() - b.ultimaMudanca >= DEBOUNCE_MS && leitura != b.estado) {
    b.estado = leitura;
    return b.estado == LOW;   // pull-up: apertado = LOW
  }
  return false;
}

void lerBotoes() {
  bool c = apertou(btnChegada);
  bool a = apertou(btnAtendido);

  if ((c || a) && btnChegada.estado == LOW && btnAtendido.estado == LOW) {
    Serial.println("Os dois botoes ao mesmo tempo, ignorado");
    acenderVermelho();
    mostrarAviso("1 botao por vez");
    return;
  }

  if (c) chegada();
  if (a) atendido();
}

void listarEventos() {
  xSemaphoreTake(travaEventos, portMAX_DELAY);
  uint32_t total = totalEventos;
  uint32_t inicio = total > MAX_EVENTOS ? total - MAX_EVENTOS : 0;
  Evento copia[MAX_EVENTOS];
  for (uint32_t i = inicio; i < total; i++) copia[i - inicio] = eventos[i % MAX_EVENTOS];
  xSemaphoreGive(travaEventos);

  Serial.printf("--- eventos na memoria: %lu (total: %lu) ---\n",
                (unsigned long)(total - inicio), (unsigned long)total);
  for (uint32_t i = inicio; i < total; i++) {
    Evento& e = copia[i - inicio];
    char hora[20];
    formatarHora(e.hora, hora, sizeof(hora));
    Serial.printf("#%lu %s %s fila=%d concl=%d\n", (unsigned long)i, nomeEvento[e.tipo], hora, e.fila, e.concluidos);
  }
}

void mostrarStatus() {
  Serial.println("--- status ---");
  Serial.printf("Chip %s | %d nucleos | %lu MHz\n", ESP.getChipModel(), ESP.getChipCores(),
                (unsigned long)ESP.getCpuFreqMHz());
  Serial.printf("Flash: %lu bytes | programa: %lu bytes\n",
                (unsigned long)ESP.getFlashChipSize(), (unsigned long)ESP.getSketchSize());
  Serial.printf("Heap: %lu total | %lu livre | %lu menor livre\n",
                (unsigned long)ESP.getHeapSize(), (unsigned long)ESP.getFreeHeap(), (unsigned long)menorHeap);
  Serial.printf("sizeof(Evento) = %d | buffer de eventos = %d bytes\n", (int)sizeof(Evento), (int)sizeof(eventos));
  Serial.printf("loop (nucleo %d): %lu us (media) | %lu us (max)\n", xPortGetCoreID(), tempoLoop, tempoLoopMax);
  if (tarefaRedeHandle) {
    Serial.printf("rede (nucleo 0): %lu us (ciclo max) | pilha livre: %u bytes\n", tempoRedeMax,
                  (unsigned)uxTaskGetStackHighWaterMark(tarefaRedeHandle));
  }
  Serial.printf("WiFi: %s | MQTT: %s | NTP: %s\n", wifiConectado ? "ok" : "off",
                mqttConectado ? "ok" : "off", horaValida(horaAtual()) ? "ok" : "pendente");
  Serial.printf("Fila: %d | Concluidos: %d | Eventos: %lu (enviados %lu)\n",
                fila, concluidos, (unsigned long)totalEventos, (unsigned long)enviados);
}

void lerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'c' || c == 'C') chegada();
    else if (c == 'a' || c == 'A') atendido();
    else if (c == 'l' || c == 'L') listarEventos();
    else if (c == 's' || c == 'S') mostrarStatus();
    else if (c != '\n' && c != '\r' && c != ' ')
      Serial.println("Comando invalido. Use: c, a, l ou s");
  }
}


// ---------- nucleo 0: rede ----------

bool publicarEvento(uint32_t seq, const Evento& e) {
  char msg[192];
  snprintf(msg, sizeof(msg),
           "{\"seq\":%lu,\"tipo\":\"%s\",\"ts\":%lu,\"sync\":%s,\"fila\":%d,\"concluidos\":%d,\"origem\":\"WOKWI\"}",
           (unsigned long)seq, nomeEvento[e.tipo], (unsigned long)e.hora,
           horaValida(e.hora) ? "true" : "false", e.fila, e.concluidos);
  return mqtt.publish(topicoEvento, msg);
}

// manda o que ficou no buffer (inclusive o que foi registrado sem conexao)
void enviarPendentes() {
  while (true) {
    xSemaphoreTake(travaEventos, portMAX_DELAY);
    if (totalEventos - enviados > MAX_EVENTOS) {
      Serial.printf("[MQTT] %lu eventos antigos foram perdidos (buffer cheio)\n",
                    (unsigned long)(totalEventos - enviados - MAX_EVENTOS));
      enviados = totalEventos - MAX_EVENTOS;
    }
    if (enviados >= totalEventos) {
      xSemaphoreGive(travaEventos);
      return;
    }
    uint32_t seq = enviados;
    Evento copia = eventos[seq % MAX_EVENTOS];
    xSemaphoreGive(travaEventos);

    if (!publicarEvento(seq, copia)) {
      Serial.println("[MQTT] erro ao publicar, tenta de novo depois");
      return;
    }
    enviados++;
  }
}

// backend manda {"conv_min": 12.5, "ia_min": 10.8}
void callback(char* topico, byte* payload, unsigned int tamanho) {
  if (strcmp(topico, topicoPrevisao) != 0) return;

  JsonDocument doc;
  if (deserializeJson(doc, payload, tamanho) || !doc["conv_min"].is<float>() || !doc["ia_min"].is<float>()) {
    Serial.println("[MQTT] previsao invalida, ignorando");
    return;
  }

  float conv = doc["conv_min"];
  float ia = doc["ia_min"];
  if (conv < 0 || ia < 0 || conv > 999 || ia > 999) {
    Serial.println("[MQTT] previsao fora da faixa, ignorando");
    return;
  }

  esperaConv = conv;
  esperaIA = ia;
  temPrevisao = true;
  atualizarTela = true;
  Serial.printf("[MQTT] previsao: media %.1f min | IA %.1f min\n", conv, ia);
}

void publicarStatus() {
  char msg[220];
  snprintf(msg, sizeof(msg),
           "{\"online\":true,\"fila\":%d,\"concluidos\":%d,\"heap\":%lu,\"heap_min\":%lu,\"rssi\":%d,"
           "\"uptime_s\":%lu,\"loop_us\":%lu,\"loop_max_us\":%lu,\"rede_max_us\":%lu}",
           fila, concluidos, (unsigned long)ESP.getFreeHeap(), (unsigned long)menorHeap, WiFi.RSSI(),
           millis() / 1000, tempoLoop, tempoLoopMax, tempoRedeMax);
  mqtt.publish(topicoStatus, msg, true);
}

void conectarMqtt() {
  static unsigned long ultimaTentativa = 0;
  if (ultimaTentativa != 0 && millis() - ultimaTentativa < 5000) return;
  ultimaTentativa = millis();

  // id diferente a cada tentativa: dois clientes com o mesmo id se derrubam no broker
  snprintf(clientId, sizeof(clientId), "esp32-fila-%08lx", (unsigned long)(esp_random() ^ micros()));

  Serial.println("[MQTT] conectando...");
  // last will: se cair, o broker avisa que ficou offline
  if (mqtt.connect(clientId, nullptr, nullptr, topicoStatus, 0, true, "{\"online\":false}")) {
    Serial.println("[MQTT] conectado");
    mqttConectado = true;
    mqtt.subscribe(topicoPrevisao);
    publicarStatus();
  } else {
    Serial.printf("[MQTT] falhou, rc=%d\n", mqtt.state());
  }
  atualizarTela = true;
}

void verificarWifi() {
  bool conectado = WiFi.status() == WL_CONNECTED;
  if (conectado == wifiConectado) return;

  wifiConectado = conectado;
  if (conectado) {
    Serial.print("[WIFI] conectado, IP ");
    Serial.println(WiFi.localIP());
    configTime(-3 * 3600, 0, "pool.ntp.org");
  } else {
    Serial.println("[WIFI] caiu a conexao, a fila continua funcionando");
  }
  atualizarTela = true;
}

void tarefaRede(void* parametro) {
  unsigned long ultimoStatus = 0;

  for (;;) {
    unsigned long inicio = micros();

    verificarWifi();

    if (wifiConectado) {
      if (mqtt.connected()) {
        mqtt.loop();
        enviarPendentes();
        if (millis() - ultimoStatus >= 10000) {
          ultimoStatus = millis();
          publicarStatus();
        }
      } else {
        if (mqttConectado) {
          mqttConectado = false;
          atualizarTela = true;
        }
        conectarMqtt();   // pode travar alguns segundos, mas so aqui no nucleo 0
      }
    }

    unsigned long duracao = micros() - inicio;
    if (duracao > tempoRedeMax) tempoRedeMax = duracao;

    vTaskDelay(pdMS_TO_TICKS(10));
  }
}


void setup() {
  Serial.begin(115200);
  Serial.println("Fila Virtual - Citizen Assist AI");
  Serial.println("Prototipo academico, nao e um canal oficial.");

  pinMode(BTN_CHEGADA, INPUT_PULLUP);
  pinMode(BTN_ATENDIDO, INPUT_PULLUP);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_VERMELHO, OUTPUT);

  lcd.init();
  lcd.backlight();
  escreverLinha(0, "Citizen Assist");
  escreverLinha(1, "Fila Virtual");

  digitalWrite(LED_VERDE, HIGH);
  digitalWrite(LED_VERMELHO, HIGH);
  delay(400);
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_VERMELHO, LOW);

  travaEventos = xSemaphoreCreateMutex();

  mqtt.setServer(broker, porta);
  mqtt.setCallback(callback);
  mqtt.setBufferSize(512);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(ssid, senha, 6);   // canal 6 deixa a conexao mais rapida no Wokwi
  Serial.println("[WIFI] conectando...");

  // a rede roda no nucleo 0 (o mesmo do Wi-Fi do ESP32); o loop fica no nucleo 1
  xTaskCreatePinnedToCore(tarefaRede, "rede", 8192, NULL, 1, &tarefaRedeHandle, 0);

  menorHeap = ESP.getFreeHeap();
  mostrarStatus();
}

void loop() {
  unsigned long inicio = micros();

  lerBotoes();
  lerSerial();
  apagarLeds();

  if (atualizarTela) desenharTela();

  uint32_t heap = ESP.getFreeHeap();
  if (heap < menorHeap) menorHeap = heap;

  unsigned long duracao = micros() - inicio;
  if (duracao > tempoLoopMax) tempoLoopMax = duracao;
  tempoLoop = (tempoLoop * 15 + duracao) / 16;

  delay(1);
}
