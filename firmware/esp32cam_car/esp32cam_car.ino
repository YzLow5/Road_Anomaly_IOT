// =====================================================================
//  ESP32-CAM trên xe — đồ án IoT phát hiện bất thường mặt đường
//
//  Board: "AI Thinker ESP32-CAM" (gói esp32 của Espressif trong Arduino IDE)
//  Sửa config.h trước khi nạp.
//
//  Cổng 80:
//    GET /                     trang xem thử + nút thử còi
//    GET /capture              1 ảnh JPEG (dùng chụp dataset)
//    GET /alert?type=pothole   còi kêu tít dài 3 lần
//    GET /alert?type=speed_bump còi kêu tít ngắn 2 lần
//    GET /status               JSON trạng thái
//  Cổng 81:
//    GET /stream               MJPEG cho laptop chạy model
//
//  Còi được điều khiển không chặn (non-blocking) trong loop(), nên xe vẫn
//  stream bình thường trong lúc kêu.
// =====================================================================

#include "esp_camera.h"
#include "esp_http_server.h"
#include <WiFi.h>
#include <ArduinoOTA.h>
#include "config.h"

// ── Chân camera của board AI Thinker ─────────────────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_LED_PIN      4

httpd_handle_t controlHttpd = NULL;
httpd_handle_t streamHttpd  = NULL;

// =====================================================================
//  Còi: bộ phát mẫu tiếng kêu không chặn
// =====================================================================
struct BeepPattern { uint8_t count; uint16_t onMs; uint16_t offMs; };
const BeepPattern PATTERN_POTHOLE    = {3, 400, 150};   // ổ gà: tít dài 3 lần
const BeepPattern PATTERN_SPEED_BUMP = {2, 120, 120};   // gờ: tít tít ngắn

volatile int  pendingAlert = 0;          // 0 = không, 1 = ổ gà, 2 = gờ (set từ HTTP handler)
BeepPattern   playing      = {0, 0, 0};
uint8_t       beepsLeft    = 0;
bool          buzzerOn     = false;
unsigned long phaseUntil   = 0;

uint32_t      alertCount   = 0;
char          lastAlert[16] = "none";
unsigned long lastAlertAt  = 0;

void buzzer(bool on) {
  buzzerOn = on;
#if BUZZER_PASSIVE
  if (on) tone(BUZZER_PIN, BUZZER_TONE_HZ); else noTone(BUZZER_PIN);
#else
  digitalWrite(BUZZER_PIN, (on != (bool)BUZZER_ACTIVE_LOW) ? HIGH : LOW);
#endif
}

void startPattern(const BeepPattern &p) {
  playing    = p;
  beepsLeft  = p.count;
  buzzer(true);
  phaseUntil = millis() + p.onMs;
}

void updateBuzzer() {
  int req = pendingAlert;
  if (req) {
    pendingAlert = 0;
    startPattern(req == 1 ? PATTERN_POTHOLE : PATTERN_SPEED_BUMP);   // lệnh mới ghi đè lệnh cũ
  }
  if (beepsLeft == 0 || (long)(millis() - phaseUntil) < 0) return;

  if (buzzerOn) {
    buzzer(false);
    beepsLeft--;
    phaseUntil = millis() + playing.offMs;
  } else {
    buzzer(true);
    phaseUntil = millis() + playing.onMs;
  }
}

// =====================================================================
//  HTTP handlers — cổng 80
// =====================================================================
static esp_err_t sendCors(httpd_req_t *req) {
  return httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
}

static esp_err_t alertHandler(httpd_req_t *req) {
  char query[64] = {0};
  char type[16]  = {0};
  sendCors(req);
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK ||
      httpd_query_key_value(query, "type", type, sizeof(type)) != ESP_OK) {
    httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "thieu ?type=pothole|speed_bump");
    return ESP_FAIL;
  }
  if (strcmp(type, "pothole") == 0)         pendingAlert = 1;
  else if (strcmp(type, "speed_bump") == 0) pendingAlert = 2;
  else {
    httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "type phai la pothole hoac speed_bump");
    return ESP_FAIL;
  }
  alertCount++;
  strncpy(lastAlert, type, sizeof(lastAlert) - 1);
  lastAlertAt = millis();
  httpd_resp_set_type(req, "text/plain");
  return httpd_resp_sendstr(req, "OK");
}

static esp_err_t statusHandler(httpd_req_t *req) {
  char json[320];
  snprintf(json, sizeof(json),
    "{\"device\":\"%s\",\"ip\":\"%s\",\"rssi\":%d,\"uptime_s\":%lu,"
    "\"free_heap\":%u,\"psram\":%s,\"alerts\":%u,\"last_alert\":\"%s\","
    "\"last_alert_s_ago\":%lu,\"buzzer_pin\":%d}",
    OTA_HOSTNAME, WiFi.localIP().toString().c_str(), WiFi.RSSI(), millis() / 1000,
    ESP.getFreeHeap(), psramFound() ? "true" : "false", alertCount, lastAlert,
    lastAlertAt ? (millis() - lastAlertAt) / 1000 : 0, BUZZER_PIN);
  sendCors(req);
  httpd_resp_set_type(req, "application/json");
  return httpd_resp_sendstr(req, json);
}

static esp_err_t captureHandler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }
  sendCors(req);
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  esp_err_t res = httpd_resp_send(req, (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return res;
}

static const char INDEX_HTML[] = R"rawliteral(<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Xe ESP32-CAM</title>
<style>body{font-family:sans-serif;background:#111;color:#eee;margin:0;padding:16px;text-align:center}
img{max-width:100%;border-radius:8px}button{margin:8px;padding:10px 16px;font-size:16px;border-radius:6px;border:0;cursor:pointer}
#s{color:#aaa;font-size:14px}</style></head><body>
<h2>Xe ESP32-CAM</h2><img id="v"><div>
<button onclick="a('speed_bump')">Thử còi: gờ giảm tốc</button>
<button onclick="a('pothole')">Thử còi: ổ gà</button></div><div id="s"></div>
<script>
document.getElementById('v').src='http://'+location.hostname+':81/stream';
function a(t){fetch('/alert?type='+t)}
async function st(){try{const j=await (await fetch('/status')).json();
document.getElementById('s').textContent='IP '+j.ip+' · Wi-Fi '+j.rssi+' dBm · chạy '+j.uptime_s+' s · đã báo '+j.alerts+' lần'}catch(e){}}
setInterval(st,2000);st();
</script></body></html>)rawliteral";

static esp_err_t indexHandler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html; charset=utf-8");
  return httpd_resp_send(req, INDEX_HTML, HTTPD_RESP_USE_STRLEN);
}

// =====================================================================
//  HTTP handler — cổng 81: stream MJPEG
// =====================================================================
#define PART_BOUNDARY "123456789000000000000987654321"
static const char *STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char *STREAM_BOUNDARY     = "\r\n--" PART_BOUNDARY "\r\n";
static const char *STREAM_PART         = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

static esp_err_t streamHandler(httpd_req_t *req) {
  char partHeader[64];
  esp_err_t res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;
  sendCors(req);

  while (true) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      res = ESP_FAIL;
      break;
    }
    size_t hlen = snprintf(partHeader, sizeof(partHeader), STREAM_PART, fb->len);
    res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, partHeader, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;   // laptop ngắt kết nối
  }
  return res;
}

void startServers() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.max_uri_handlers = 8;

  httpd_uri_t indexUri   = {"/",        HTTP_GET, indexHandler,   NULL};
  httpd_uri_t captureUri = {"/capture", HTTP_GET, captureHandler, NULL};
  httpd_uri_t alertUri   = {"/alert",   HTTP_GET, alertHandler,   NULL};
  httpd_uri_t statusUri  = {"/status",  HTTP_GET, statusHandler,  NULL};
  if (httpd_start(&controlHttpd, &config) == ESP_OK) {
    httpd_register_uri_handler(controlHttpd, &indexUri);
    httpd_register_uri_handler(controlHttpd, &captureUri);
    httpd_register_uri_handler(controlHttpd, &alertUri);
    httpd_register_uri_handler(controlHttpd, &statusUri);
  }

  config.server_port += 1;   // 81
  config.ctrl_port   += 1;
  httpd_uri_t streamUri = {"/stream", HTTP_GET, streamHandler, NULL};
  if (httpd_start(&streamHttpd, &config) == ESP_OK) {
    httpd_register_uri_handler(streamHttpd, &streamUri);
  }
}

// =====================================================================
//  Camera, Wi-Fi, OTA
// =====================================================================
bool initCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer   = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk = XCLK_GPIO_NUM;   c.pin_pclk = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM; c.pin_href = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM; c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn = PWDN_GPIO_NUM;   c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size   = CAMERA_FRAME_SIZE;
  c.jpeg_quality = CAMERA_JPEG_QUALITY;
  if (psramFound()) {
    c.fb_count     = 2;
    c.fb_location  = CAMERA_FB_IN_PSRAM;
    c.grab_mode    = CAMERA_GRAB_LATEST;   // luôn lấy khung mới nhất → giảm trễ
  } else {
    c.fb_count     = 1;
    c.fb_location  = CAMERA_FB_IN_DRAM;
    c.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
  }

  if (esp_camera_init(&c) != ESP_OK) return false;

  sensor_t *s = esp_camera_sensor_get();
  s->set_vflip(s, CAMERA_VFLIP);
  s->set_hmirror(s, CAMERA_HMIRROR);
  return true;
}

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);   // tắt tiết kiệm điện Wi-Fi để stream mượt
#if USE_STATIC_IP
  IPAddress ip(STATIC_IP), gw(GATEWAY_IP), mask(SUBNET_MASK);
  WiFi.config(ip, gw, mask, gw);
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Đang kết nối Wi-Fi \"%s\"", WIFI_SSID);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
}

void setupOTA() {
  ArduinoOTA.setHostname(OTA_HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);
  ArduinoOTA.onStart([]() { buzzer(false); Serial.println("OTA: bắt đầu nạp code qua Wi-Fi"); });
  ArduinoOTA.onEnd([]()   { Serial.println("OTA: xong, khởi động lại"); });
  ArduinoOTA.onError([](ota_error_t e) { Serial.printf("OTA lỗi %u\n", e); });
  ArduinoOTA.begin();
}

void setup() {
  Serial.begin(115200);
  Serial.println("\n== Xe ESP32-CAM ==");

  pinMode(FLASH_LED_PIN, OUTPUT);
  digitalWrite(FLASH_LED_PIN, LOW);
  pinMode(BUZZER_PIN, OUTPUT);
  buzzer(false);

  if (!initCamera()) {
    Serial.println("LỖI: không khởi động được camera — kiểm tra cáp camera, nguồn 5V");
    delay(3000);
    ESP.restart();
  }

  connectWiFi();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("LỖI: không vào được Wi-Fi — kiểm tra tên/mật khẩu, mạng phải là 2.4GHz");
    delay(3000);
    ESP.restart();
  }

  setupOTA();
  startServers();

  String ip = WiFi.localIP().toString();
  Serial.println("Sẵn sàng:");
  Serial.println("  Xem thử : http://" + ip + "/");
  Serial.println("  Stream  : http://" + ip + ":81/stream");
  Serial.println("  Thử còi : http://" + ip + "/alert?type=pothole");

  // Kêu 1 tiếng ngắn báo đã sẵn sàng
  startPattern({1, 80, 0});
}

unsigned long lastWifiCheck = 0;

void loop() {
  ArduinoOTA.handle();
  updateBuzzer();

  if (millis() - lastWifiCheck > 5000) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Mất Wi-Fi, đang kết nối lại…");
      WiFi.reconnect();
    }
  }
  delay(2);
}
