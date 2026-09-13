/**
 * frontend/api.js
 * Shared helper for talking to the GlobeTrotter API Gateway.
 * Every page includes this file before its own script.
 */
const API_BASE = "https://globetrotter-gateway.onrender.com";
const INACTIVITY_LIMIT_MS = 20 * 60 * 1000; // 20 minutes

function saveSession(token, username, isAdmin) {
  localStorage.setItem("gt_token", token);
  localStorage.setItem("gt_username", username);
  localStorage.setItem("gt_is_admin", isAdmin ? "true" : "false");
}

function clearSession() {
  localStorage.removeItem("gt_token");
  localStorage.removeItem("gt_username");
  localStorage.removeItem("gt_is_admin");
}

function getToken() { return localStorage.getItem("gt_token"); }
function getUsername() { return localStorage.getItem("gt_username"); }
function isLoggedIn() { return !!getToken(); }
function isAdmin() { return localStorage.getItem("gt_is_admin") === "true"; }

function authHeaders() {
  const token = getToken();
  return token ? { "Authorization": `Bearer ${token}` } : {};
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function showToast(message, isError = false) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  toast.className = "toast" + (isError ? " error" : "");
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("show"));
  setTimeout(() => {
    toast.classList.remove("show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/**
 * If the session has expired or become invalid, clear it and send the
 * user to the login page automatically, instead of showing a confusing
 * "authentication required" error on screen.
 */
function forceReauth() {
  const wasLoggedIn = isLoggedIn();
  clearSession();
  if (wasLoggedIn && !window.location.pathname.endsWith("login.html")) {
    showToast("Your session expired — please log in again.", true);
    setTimeout(() => { window.location.href = "login.html"; }, 1200);
  }
}

async function parseJsonSafe(resp) {
  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error("SERVER_WAKING_UP");
  }
}

async function fetchWithWakeupRetry(fetchFn, requiresAuth = false) {
  const delays = [5000, 10000, 15000, 20000];

  const attempt = async () => {
    try {
      return await fetchFn();
    } catch (err) {
      if (requiresAuth && err.status === 401) {
        forceReauth();
      }
      throw err;
    }
  };

  try {
    return await attempt();
  } catch (err) {
    if (err.message !== "SERVER_WAKING_UP") throw err;
    for (const delay of delays) {
      await sleep(delay);
      try {
        return await attempt();
      } catch (err2) {
        if (err2.message !== "SERVER_WAKING_UP") throw err2;
      }
    }
    throw new Error("The server is taking longer than usual to start. Please try again in a moment.");
  }
}

async function apiRegister(username, password, preferences = [], adminCode = "") {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password, preferences, admin_code: adminCode }),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Registration failed"); e.status = resp.status; throw e; }
    return data;
  });
}

async function apiLogin(username, password) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Login failed"); e.status = resp.status; throw e; }

    let isAdminUser = false;
    try {
      const verifyResp = await fetch(`${API_BASE}/verify`, {
        headers: { "Authorization": `Bearer ${data.token}` },
      });
      const verifyData = await parseJsonSafe(verifyResp);
      isAdminUser = !!verifyData.is_admin;
    } catch (err) {
      isAdminUser = false;
    }

    saveSession(data.token, username, isAdminUser);
    resetInactivityTimer();
    return data;
  });
}

function apiLogout() {
  clearSession();
}

async function apiGetPlaces(filters = {}) {
  return fetchWithWakeupRetry(async () => {
    const params = new URLSearchParams(filters);
    const resp = await fetch(`${API_BASE}/destinations?${params.toString()}`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load places"); e.status = resp.status; throw e; }
    return data;
  });
}

async function apiGetPlace(id) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Place not found"); e.status = resp.status; throw e; }
    return data;
  });
}

async function apiCreatePlace(place) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(place),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to add place"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiUpdatePlace(id, updates) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(updates),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to update place"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiDeletePlace(id) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to delete place"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetReviews(placeId) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${placeId}/reviews`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load reviews"); e.status = resp.status; throw e; }
    return data;
  });
}

async function apiSubmitReview(placeId, rating, comment) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${placeId}/reviews`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ rating, comment }),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to submit review"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetRecommendations() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/recommendations`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load recommendations"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetItineraries() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load itineraries"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiCreateItinerary(itinerary) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(itinerary),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to create itinerary"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiUpdateItinerary(id, updates) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(updates),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to update itinerary"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetAllUsers() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/users`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load users"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiDeleteUser(username) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/users/${username}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to delete user"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetAllItineraries() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries/all`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load itineraries"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

async function apiGetSettings() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/settings`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to load settings"); e.status = resp.status; throw e; }
    return data;
  });
}

async function apiUpdateSettings(updates) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(updates),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) { const e = new Error(data.error || "Failed to update settings"); e.status = resp.status; throw e; }
    return data;
  }, true);
}

function toRadShared(deg) { return deg * (Math.PI / 180); }

function haversineDistanceKmShared(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = toRadShared(lat2 - lat1);
  const dLon = toRadShared(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRadShared(lat1)) * Math.cos(toRadShared(lat2)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// ---------------------------------------------------------------------------
// Auto-logout after inactivity
// ---------------------------------------------------------------------------
let inactivityTimer;
function resetInactivityTimer() {
  clearTimeout(inactivityTimer);
  if (!isLoggedIn()) return;
  inactivityTimer = setTimeout(() => {
    clearSession();
    showToast("Logged out due to inactivity.", true);
    if (!window.location.pathname.endsWith("login.html")) {
      setTimeout(() => { window.location.href = "login.html"; }, 1200);
    }
  }, INACTIVITY_LIMIT_MS);
}
["click", "keydown", "mousemove", "scroll", "touchstart"].forEach((evt) =>
  document.addEventListener(evt, resetInactivityTimer)
);
resetInactivityTimer();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch((err) => console.log("SW registration failed:", err));
  });
}


// ---------------------------------------------------------------------------
// Chatbot — simple rule-based assistant over the existing places API
// ---------------------------------------------------------------------------
function injectChatbot() {
  const bubble = document.createElement("button");
  bubble.id = "chatbot-bubble";
  bubble.innerHTML = "💬";
  bubble.title = "Chat with Explore Fako";

  const panel = document.createElement("div");
  panel.id = "chatbot-panel";
  panel.innerHTML = `
    <div class="cb-header">
      <span>Explore Fako Assistant</span>
      <button id="cb-close">✕</button>
    </div>
    <div class="cb-messages" id="cb-messages"></div>
    <div class="cb-input-row">
      <input type="text" id="cb-input" placeholder="Ask me e.g. 'best hotels in Buea'">
      <button id="cb-send">Send</button>
    </div>
  `;

  document.body.appendChild(bubble);
  document.body.appendChild(panel);

  bubble.addEventListener("click", () => {
    panel.classList.toggle("open");
    if (panel.classList.contains("open") && document.getElementById("cb-messages").children.length === 0) {
      addBotMessage("Hi! I'm the Explore Fako assistant. Ask me things like <em>\"restaurants in Limbe\"</em>, <em>\"5 star hotels\"</em>, or <em>\"how do I plan a trip?\"</em>");
    }
  });
  document.getElementById("cb-close").addEventListener("click", () => panel.classList.remove("open"));

  const input = document.getElementById("cb-input");
  const sendBtn = document.getElementById("cb-send");
  const send = () => {
    const text = input.value.trim();
    if (!text) return;
    addUserMessage(text);
    input.value = "";
    handleChatQuery(text);
  };
  sendBtn.addEventListener("click", send);
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
}

function addUserMessage(text) {
  const msgs = document.getElementById("cb-messages");
  const div = document.createElement("div");
  div.className = "cb-msg user";
  div.textContent = text;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

function addBotMessage(html) {
  const msgs = document.getElementById("cb-messages");
  const div = document.createElement("div");
  div.className = "cb-msg bot";
  div.innerHTML = html;
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
}

async function handleChatQuery(rawText) {
  const text = rawText.toLowerCase();

  if (/\b(hi|hello|hey|good (morning|afternoon|evening))\b/.test(text)) {
    addBotMessage("Hello! Try asking about a category (hospital, hotel, restaurant, pharmacy, school), a town (Buea or Limbe), or say \"help\".");
    return;
  }
  if (/\bhelp\b/.test(text)) {
    addBotMessage(`I can help you:<br>• Find places — "hotels in Buea"<br>• Find top-rated places — "5 star restaurants"<br>• Plan a trip — say "itinerary"<br>• Get fares — open any place page and tap "Find distance & fare"`);
    return;
  }
  if (/itinerar/.test(text)) {
    addBotMessage(`You can plan and save trips on the <a href="itinerary.html">My Itineraries</a> page — it keeps your history so you can revisit places anytime.`);
    return;
  }
  if (/(fare|taxi|bike|moto|price to get|transport)/.test(text)) {
    addBotMessage(`Open any place's page and tap <strong>"Find distance & fare"</strong> — I'll estimate the taxi/bike cost from your current location.`);
    return;
  }

  const categories = ["hospital", "hotel", "restaurant", "pharmacy", "school"];
  const foundCategory = categories.find((c) => text.includes(c) || text.includes(c + "s"));
  const foundTown = ["buea", "limbe"].find((t) => text.includes(t));

  let minRating = null;
  const starMatch = text.match(/(\d)(?:\s*-?\s*star|\s*star)/);
  if (starMatch) minRating = parseFloat(starMatch[1]);
  else if (/\b(best|top rated|top-rated)\b/.test(text)) minRating = 4;

  const filters = {};
  if (foundCategory) filters.category = foundCategory;
  if (foundTown) filters.town = foundTown;
  if (minRating) filters.min_rating = minRating;

  if (Object.keys(filters).length === 0) {
    filters.q = rawText;
  }

  try {
    addBotMessage("Searching…");
    const places = await apiGetPlaces(filters);
    const messagesEl = document.getElementById("cb-messages");
    messagesEl.lastChild.remove();

    if (!places || places.length === 0) {
      addBotMessage("I couldn't find a match. Try a different category, town, or check the <a href=\"browse.html\">Browse page</a>.");
      return;
    }
    const top = places.sort((a, b) => (b.average_rating || 0) - (a.average_rating || 0)).slice(0, 5);
    const listHtml = top.map((p) =>
      `<a class="cb-place-link" href="place.html?id=${p.id}">★ ${p.average_rating ?? "—"} — ${p.name} (${p.town || ""})</a>`
    ).join("");
    addBotMessage(`Here's what I found:${listHtml}`);
  } catch (err) {
    addBotMessage("Sorry, I couldn't search right now — please try again in a moment.");
  }
}

document.addEventListener("DOMContentLoaded", injectChatbot);