/* ══════════════════════════════════════════════
   AGROMIND — main.js
══════════════════════════════════════════════ */

// ── DARK MODE ──────────────────────────────────
function toggleDark() {
  const html = document.documentElement;
  const isDark = html.getAttribute("data-theme") === "dark";
  const next = isDark ? "light" : "dark";
  html.setAttribute("data-theme", next);
  const icon = document.getElementById("theme-icon");
  if (icon) icon.textContent = next === "dark" ? "☀️" : "🌙";
  localStorage.setItem("agro-theme", next);
}

(function initTheme() {
  const saved = localStorage.getItem("agro-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  const icon = document.getElementById("theme-icon");
  if (icon) icon.textContent = saved === "dark" ? "☀️" : "🌙";
})();

// ── ANIMATED BACKGROUND ─────────────────────────
(function initCanvas() {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  let W, H, particles = [];

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function Particle() {
    this.x  = Math.random() * W;
    this.y  = Math.random() * H;
    this.r  = Math.random() * 1.8 + 0.4;
    this.vx = (Math.random() - 0.5) * 0.3;
    this.vy = (Math.random() - 0.5) * 0.3;
    this.a  = Math.random() * 0.5 + 0.1;
  }
  Particle.prototype.update = function () {
    this.x += this.vx; this.y += this.vy;
    if (this.x < 0) this.x = W;
    if (this.x > W) this.x = 0;
    if (this.y < 0) this.y = H;
    if (this.y > H) this.y = 0;
  };

  function init() {
    resize();
    particles = Array.from({ length: 80 }, () => new Particle());
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const color = isDark ? "169,227,75" : "90,158,15";

    particles.forEach(p => {
      p.update();
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color},${p.a})`;
      ctx.fill();
    });

    // Draw connecting lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx*dx + dy*dy);
        if (dist < 120) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(${color},${0.06 * (1 - dist/120)})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", resize);
  init();
  draw();
})();

// ── MINI CHART ──────────────────────────────────
let miniChartInstance = null;

// ── PREDICT ─────────────────────────────────────
async function predict() {
  const btnText   = document.getElementById("btn-text");
  const btnLoader = document.getElementById("btn-loader");
  if (btnText)   btnText.style.display   = "none";
  if (btnLoader) btnLoader.style.display = "inline-flex";

  const state    = document.getElementById("state").value;
  const district = document.getElementById("district").value;
  const season   = document.getElementById("season").value;
  const area     = document.getElementById("area").value;

// ✅ FRONTEND VALIDATION
if (!state || !district || !season || !area) {
  alert("⚠️ Please fill all fields before predicting.");
  return;
}

const payload = {
  state,
  district,
  season,
  area: parseFloat(area),
};

  try {
    const res  = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    console.log("PREDICT RESPONSE:", data);
    console.log("WORST CASE:", data.worst_case);

// ✅ SAFE ERROR CHECK (won’t affect UI)
if (data.error) {
  alert("❌ " + data.error);
  return;
}

renderResults(data);
    sessionStorage.setItem("lastPrediction", JSON.stringify(data));
  } catch (err) {
    alert("❌ Could not connect to server. Make sure Flask is running.");
  } finally {
    if (btnText)   btnText.style.display   = "inline";
    if (btnLoader) btnLoader.style.display = "none";
  }
}

function renderResults(data) {
  document.getElementById("placeholder").style.display = "none";
  const resultsEl = document.getElementById("results");
  resultsEl.style.display = "block";

  // Hero
  document.getElementById("best-crop").textContent     = data.top3[0].crop;
  document.getElementById("production-text").textContent = `📦 Expected yield: ${data.production} tonnes`;
  const guide = data.advisory.find(item => item.label === "Planting Guide");

if (guide) {
    document.getElementById("plant-count").textContent = "🌱 " + guide.sub[0];
}

  // Top 3
  const medals = ["🥇","🥈","🥉"];
  document.getElementById("top3-cards").innerHTML = data.top3.map((c, i) => `
    <div class="top3-item">
      <div class="top3-rank">${medals[i]}</div>
      <div class="top3-name">${c.crop}</div>
      <div class="top3-conf">${c.confidence}% Probability</div>
      <div class="conf-bar">
        <div class="conf-fill" style="width:0%" data-width="${c.confidence}%"></div>
      </div>
    </div>
  `).join("");

  // Animate conf bars after DOM insert
  setTimeout(() => {
    document.querySelectorAll(".conf-fill").forEach(el => {
      el.style.width = el.dataset.width;
    });
  }, 50);


    // Advisory — structured rendering
  const advEl = document.getElementById("advisory-list");
  if (advEl && data.advisory) {
    advEl.innerHTML = data.advisory.map(item => {
      if (item.sub && item.sub.length) {
        // Planting guide — sub-bullet section
        return `
          <div class="advisory-item advisory-section">
            <span class="adv-icon">${item.icon}</span>
            <div class="adv-body">
              <span class="adv-label">${item.label}</span>
              <ul class="adv-sub-list">
                ${item.sub.map(s => `<li>${s}</li>`).join("")}
              </ul>
            </div>
          </div>`;
      }
      return `
        <div class="advisory-item">
          <span class="adv-icon">${item.icon}</span>
          <div class="adv-body">
            <span class="adv-label">${item.label}:</span>
            <span class="adv-value">${item.value}</span>
          </div>
        </div>`;
    }).join("");
  }
  // Alternative crops
  const altWrap = document.getElementById("alternative-crops");
  if (altWrap) {
    if (data.alternatives && data.alternatives.length > 0) {
    altWrap.innerHTML = data.alternatives.map(c => `
      <div class="alt-crop-card">
        <div class="alt-crop-name">${c.crop}</div>
        <div class="alt-crop-prob">${c.confidence}% Probability</div>
        <div class="alt-crop-reason">${c.reason}</div>
      </div>
    `).join("");
  } else {
    altWrap.innerHTML = `<div class="muted-text">No alternative crops available.</div>`;
    }
  }

  // Combo crop suggestion
  const comboBox = document.getElementById("combo-crop-box");

if (comboBox) {
  if (data.combo_crop) {
    const mix = data.combo_crop.mix || "No combo suggestion available";
    const mainCrop = data.combo_crop.main_crop || "Not available";
    const partnerCrop = data.combo_crop.partner_crop || "Optional";
    const reason = data.combo_crop.reason || "This crop is generally grown independently.";

    comboBox.innerHTML = `
      <div class="combo-card">
        <div class="combo-main">${mix}</div>
        <div class="combo-sub">
          Main Crop: ${mainCrop} | Partner Crop: ${partnerCrop}
        </div>
        <div class="combo-reason">${reason}</div>
      </div>
    `;
  } else {
    comboBox.innerHTML = `
      <div class="combo-card">
        <div class="combo-main">No combo suggestion available</div>
        <div class="combo-sub">Main Crop: Not available | Partner Crop: Optional</div>
        <div class="combo-reason">This crop is generally grown independently.</div>
      </div>
    `;
  }
}

// Worst-case / risk alert
const riskBox = document.getElementById("worst-case-box");

if (riskBox) {
  console.log("Risk box found");
  console.log("Worst case data:", data.worst_case);

  if (data.worst_case && data.worst_case.title) {
    const levelClass =
      data.worst_case.level === "High" ? "risk-high" :
      data.worst_case.level === "Medium" ? "risk-medium" :
      "risk-low";

    riskBox.innerHTML = `
      <div class="risk-card ${levelClass}">
        <div class="risk-title">${data.worst_case.title}</div>
        <div class="risk-message">${data.worst_case.message}</div>
        <div class="risk-advice">${data.worst_case.advice}</div>
      </div>
    `;
  } else {
    riskBox.innerHTML = `<div class="muted-text">No risk alert available.</div>`;
  }
}

  // Mini chart
  const isDark = document.documentElement.getAttribute("data-theme") === "dark";
  const ctx = document.getElementById("miniChart").getContext("2d");
  if (miniChartInstance) miniChartInstance.destroy();

  miniChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.top3.map(c => c.crop),
      datasets: [{
        label: "Confidence %",
        data: data.top3.map(c => c.confidence),
        backgroundColor: ["rgba(169,227,75,0.85)","rgba(169,227,75,0.5)","rgba(169,227,75,0.3)"],
        borderRadius: 10,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: {
          beginAtZero: true, max: 100,
          grid: { color: isDark ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.05)" },
          ticks: { color: isDark ? "#7a9070" : "#4a6a35" }
        },
        x: {
          grid: { display: false },
          ticks: { color: isDark ? "#7a9070" : "#4a6a35", font: { family: "DM Sans" } }
        }
      }
    }
  });
}

// ── CHATBOT ──────────────────────────────────────
async function sendChat() {
  const input = document.getElementById("chat-input");
  const box = document.getElementById("chat-box");
  const msg = input.value.trim();
  if (!msg) return;

  box.innerHTML += `
    <div class="chat-msg user">
      <div class="msg-bubble">${msg}</div>
      <div class="msg-avatar">👤</div>
    </div>`;
  input.value = "";
  box.scrollTop = box.scrollHeight;

  // ✅ Typing indicator
  const typingId = "typing-" + Date.now();
  box.innerHTML += `
    <div class="chat-msg bot typing-row" id="${typingId}">
      <div class="msg-avatar">🌿</div>
      <div class="msg-bubble typing-bubble">
        <span></span><span></span><span></span>
      </div>
    </div>`;
  box.scrollTop = box.scrollHeight;

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg })
    });

    const data = await res.json();

    // ✅ Fake natural delay so reply doesn’t appear instantly
    await new Promise(resolve => setTimeout(resolve, 1200));

    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    box.innerHTML += `
      <div class="chat-msg bot">
        <div class="msg-avatar">🌿</div>
        <div class="msg-bubble">${data.reply}</div>
      </div>`;
  } catch {
    const typingEl = document.getElementById(typingId);
    if (typingEl) typingEl.remove();

    box.innerHTML += `
      <div class="chat-msg bot">
        <div class="msg-avatar">🌿</div>
        <div class="msg-bubble">⚠️ Server not reachable.</div>
      </div>`;
  }

  box.scrollTop = box.scrollHeight;
}

async function addPost() {
  const name = document.getElementById("post-name").value.trim();
  const msg  = document.getElementById("post-msg").value.trim();
  if (!name || !msg) { alert("Please enter your name and message."); return; }

  try {
    await fetch("/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, message: msg })
    });
    document.getElementById("post-msg").value = "";
    loadPosts();
  } catch {
    alert("⚠️ Could not post. Is Flask running?");
  }
}

async function loadAllCrops() {
  try {
    const kpis = document.querySelectorAll(".kpi-val");

    // ✅ Show loading state FIRST
    kpis.forEach(k => k.innerText = "...");

    const res = await fetch("/get_analytics");
    const data = await res.json();

    console.log(data);

    if (!data || data.length === 0) {
      kpis.forEach(k => k.innerText = "0");
      return;
    }

    // ✅ DEFINE crops
    const crops = data.map(d => d.crop);

    // KPI calculations
    const highWater = data.filter(d => d.water > 70).length;
    const highProfit = data.filter(d => d.profit > 70).length;
    const highRisk = data.filter(d => d.risk > 60).length;

    // ✅ UPDATE UI (ONLY AFTER DATA READY)
    kpis[0].innerText = crops.length;
    kpis[1].innerText = highWater;
    kpis[2].innerText = highProfit;
    kpis[3].innerText = highRisk;

  } catch (err) {
    console.error("KPI Error:", err);

    // fallback UI
    const kpis = document.querySelectorAll(".kpi-val");
    kpis.forEach(k => k.innerText = "0");
  }
}

// Load districts
async function loadDistricts() {
  const state = document.getElementById("state")?.value;
  const distSel = document.getElementById("district");

  if (!state || !distSel) return;

  distSel.innerHTML = "<option>Loading...</option>";

  try {
    const res = await fetch(`/get_districts/${encodeURIComponent(state)}`);
    const districts = await res.json();

    distSel.innerHTML = districts.map(d => `<option>${d}</option>`).join("");
  } catch {
    distSel.innerHTML = "<option>Error loading</option>";
  }
}

//weather
async function loadWeather() {
  navigator.geolocation.getCurrentPosition(
    async (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      const res = await fetch(`/weather?lat=${lat}&lon=${lon}`);
      const data = await res.json();

      console.log(data);

      // ✅ Update UI
      document.getElementById("temp").innerText = data.temp + "°C";
      document.getElementById("humidity").innerText = data.hum + "%";
      document.getElementById("rain").innerText = data.rain;
      document.getElementById("wind").innerText = data.wind + " km/h";

      // OPTIONAL: update city name
      document.querySelector(".card-sub").innerText = data.city;
    },
    (err) => {
      console.log("Location denied, using fallback");

      // fallback Mumbai
      fetch(`/weather?lat=19.076&lon=72.877`)
        .then(res => res.json())
        .then(data => {
          document.getElementById("temp").innerText = data.temp + "°C";
          document.getElementById("humidity").innerText = data.hum + "%";
          document.getElementById("rain").innerText = data.rain;
          document.getElementById("wind").innerText = data.wind + " km/h";
        });
    }
  );
}

function restoreLastPrediction() {
  const saved = sessionStorage.getItem("lastPrediction");
  if (!saved) return;

  try {
    const data = JSON.parse(saved);
    console.log("Restoring prediction:", data);
    renderResults(data);
  } catch (err) {
    console.error("Could not restore last prediction:", err);
  }
}
window.addEventListener("DOMContentLoaded", async () => {
  // Index page
  if (window.location.pathname === "/") {
    await loadDistricts();
    restoreLastPrediction();
    loadWeather();
  }

  // Analytics page
  if (window.location.pathname === "/analytics") {
    loadAllCrops();
  }
});