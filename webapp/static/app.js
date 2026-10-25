// Dashboard: hỏi /api/status mỗi 0,5 giây, /api/events mỗi giây.
const $ = (id) => document.getElementById(id);
const NAME = { pothole: "Ổ gà", speed_bump: "Gờ giảm tốc" };
let lastEventId = 0;
let firstLoad = true;
let bannerTimer = null;

// ── Âm thanh laptop: cùng kiểu kêu với còi trên xe ──────────────────────
const PATTERN = { pothole: [3, 400, 150], speed_bump: [2, 120, 120] };
let audio = null;
function beep(label) {
  if (!$("sound").checked) return;
  audio = audio || new (window.AudioContext || window.webkitAudioContext)();
  const [count, on, off] = PATTERN[label];
  let t = audio.currentTime + 0.02;
  for (let i = 0; i < count; i++) {
    const osc = audio.createOscillator();
    const gain = audio.createGain();
    osc.type = "square";
    osc.frequency.value = 2400;
    gain.gain.value = 0.08;
    osc.connect(gain).connect(audio.destination);
    osc.start(t);
    osc.stop(t + on / 1000);
    t += (on + off) / 1000;
  }
}
// Trình duyệt chỉ cho phát âm thanh sau khi người dùng bấm vào trang.
document.addEventListener("click", () => {
  audio = audio || new (window.AudioContext || window.webkitAudioContext)();
  audio.resume();
}, { once: true });

// ── Hiển thị ─────────────────────────────────────────────────────────────
function chip(id, state, text) {
  const el = $(id);
  el.className = "chip " + (state === null ? "" : state ? "on" : "off");
  el.lastChild.textContent = text;
}

function showBanner(event) {
  const b = $("banner");
  b.className = "banner " + event.label;
  b.textContent = `⚠ ${event.label_vi.toUpperCase()} PHÍA TRƯỚC`;
  b.hidden = false;
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => (b.hidden = true), 2500);
}

function renderStatus(s) {
  chip("chip-camera", s.camera.online, `Camera: ${s.camera.online ? s.camera.kind : "mất kết nối"}`);
  const car = s.car;
  chip("chip-car", car.configured ? car.online : null,
       car.configured ? `Xe: ${car.online ? "online" : "offline"}` : "Xe: chưa cấu hình");
  chip("chip-model", s.models.length > 0, `Model: ${s.models.join(", ") || "chưa nạp"}`);
  $("offline").hidden = s.camera.online;

  $("car-ip").textContent = car.configured ? car.ip : "Chưa đặt ESP32_IP";
  $("car-state").textContent = !car.configured ? "—" : car.online
    ? `online${car.info && car.info.rssi ? ` · Wi-Fi ${car.info.rssi} dBm` : ""}` : "offline";
  const a = car.last_alert;
  $("car-alert").textContent = a ? `${a.time} · ${NAME[a.type]} · ${a.ok ? a.latency_ms + " ms" : "lỗi"}` : "—";

  $("count-pothole").textContent = s.counts.pothole;
  $("count-speed_bump").textContent = s.counts.speed_bump;
  $("cam-fps").textContent = s.camera.fps || "—";
  $("infer-ms").textContent = s.infer_ms || "—";

  $("now").textContent = s.detections.length
    ? "Đang thấy: " + s.detections.map(d => `${NAME[d.label]} ${(d.confidence * 100).toFixed(0)}%`).join(", ")
    : s.camera.online ? "Mặt đường bình thường" : "Đang chờ ảnh từ camera…";

  const last = $("last");
  if (s.last_event) {
    last.className = "last " + s.last_event.label;
    last.innerHTML = `${s.last_event.label_vi}<small>${s.last_event.time} · ${s.last_event.seconds_ago} giây trước</small>`;
  }
}

function addEvents(events) {
  if (!events.length) return;
  const body = $("log");
  body.querySelector(".empty")?.remove();
  for (const e of events) {
    const row = document.createElement("tr");
    row.innerHTML = `<td>${e.time}</td><td><span class="tag ${e.label}">${e.label_vi}</span></td>` +
                    `<td>${(e.confidence * 100).toFixed(0)}%</td>`;
    body.prepend(row);
    lastEventId = Math.max(lastEventId, e.id);
  }
  if (!firstLoad) {
    // Nhiều cảnh báo cùng lúc: hiện và kêu theo loại nguy hiểm hơn (ổ gà)
    const top = events.find(e => e.label === "pothole") || events[events.length - 1];
    showBanner(top);
    beep(top.label);
  }
}

// ── Hỏi server ───────────────────────────────────────────────────────────
async function pollStatus() {
  try { renderStatus(await (await fetch("/api/status")).json()); } catch (e) {}
}
async function pollEvents() {
  try {
    const data = await (await fetch(`/api/events?after=${lastEventId}`)).json();
    addEvents(data.events);
    firstLoad = false;
  } catch (e) {}
}

document.querySelectorAll("[data-test]").forEach(btn => btn.addEventListener("click", async () => {
  const r = await fetch("/api/test-alert", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: btn.dataset.test }),
  });
  if (!r.ok) alert((await r.json()).detail);
}));

// Ảnh MJPEG bị ngắt (server khởi động lại) thì nạp lại
$("video").addEventListener("error", () => setTimeout(() => {
  $("video").src = "/stream.mjpg?" + Date.now();
}, 2000));

pollStatus(); pollEvents();
setInterval(pollStatus, 500);
setInterval(pollEvents, 1000);
