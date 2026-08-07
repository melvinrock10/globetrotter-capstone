/**
 * frontend/api.js
 * Shared helper for talking to the GlobeTrotter API Gateway.
 * Every page includes this file before its own script.
 */
const API_BASE = "https://globetrotter-gateway.onrender.com";

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

/**
 * Safely parse a fetch Response as JSON.
 * If the server returns something that ISN'T JSON (e.g. an HTML error
 * page during a cold start), this throws a clean, friendly error instead
 * of letting the raw "Unexpected token '<'" crash bubble up to the user.
 */
async function parseJsonSafe(resp) {
  const text = await resp.text();
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error("SERVER_WAKING_UP");
  }
}

/**
 * Wraps a fetch call with one automatic retry if the server was still
 * waking up from sleep (free hosting tier). Waits 4 seconds, then tries
 * once more before giving up with a friendly message.
 */
async function fetchWithWakeupRetry(fetchFn) {
  try {
    return await fetchFn();
  } catch (err) {
    if (err.message === "SERVER_WAKING_UP") {
      await sleep(4000);
      try {
        return await fetchFn();
      } catch (err2) {
        throw new Error("The server is still starting up. Please wait a few seconds and try again.");
      }
    }
    throw err;
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
    if (!resp.ok) throw new Error(data.error || "Registration failed");
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
    if (!resp.ok) throw new Error(data.error || "Login failed");

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
    if (!resp.ok) throw new Error(data.error || "Failed to load places");
    return data;
  });
}

async function apiGetPlace(id) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Place not found");
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
    if (!resp.ok) throw new Error(data.error || "Failed to add place");
    return data;
  });
}

async function apiUpdatePlace(id, updates) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(updates),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to update place");
    return data;
  });
}

async function apiDeletePlace(id) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${id}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to delete place");
    return data;
  });
}

async function apiGetReviews(placeId) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/destinations/${placeId}/reviews`);
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to load reviews");
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
    if (!resp.ok) throw new Error(data.error || "Failed to submit review");
    return data;
  });
}

async function apiGetRecommendations() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/recommendations`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to load recommendations");
    return data;
  });
}

async function apiGetItineraries() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to load itineraries");
    return data;
  });
}

async function apiCreateItinerary(itinerary) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(itinerary),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to create itinerary");
    return data;
  });
}

async function apiGetAllUsers() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/users`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to load users");
    return data;
  });
}

async function apiDeleteUser(username) {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/users/${username}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to delete user");
    return data;
  });
}

async function apiGetAllItineraries() {
  return fetchWithWakeupRetry(async () => {
    const resp = await fetch(`${API_BASE}/itineraries/all`, { headers: authHeaders() });
    const data = await parseJsonSafe(resp);
    if (!resp.ok) throw new Error(data.error || "Failed to load itineraries");
    return data;
  });
}