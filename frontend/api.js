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

async function apiRegister(username, password, preferences = [], adminCode = "") {
  const resp = await fetch(`${API_BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, preferences, admin_code: adminCode }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Registration failed");
  return data;
}

async function apiLogin(username, password) {
  const resp = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Login failed");

  let isAdminUser = false;
  try {
    const verifyResp = await fetch(`${API_BASE}/verify`, {
      headers: { "Authorization": `Bearer ${data.token}` },
    });
    const verifyData = await verifyResp.json();
    isAdminUser = !!verifyData.is_admin;
  } catch (err) {
    // Even if this check fails, don't block a successful login
    isAdminUser = false;
  }

  saveSession(data.token, username, isAdminUser);
  return data;
}

function apiLogout() {
  clearSession();
}

async function apiGetPlaces(filters = {}) {
  const params = new URLSearchParams(filters);
  const resp = await fetch(`${API_BASE}/destinations?${params.toString()}`);
  if (!resp.ok) throw new Error("Failed to load places");
  return resp.json();
}

async function apiGetPlace(id) {
  const resp = await fetch(`${API_BASE}/destinations/${id}`);
  if (!resp.ok) throw new Error("Place not found");
  return resp.json();
}

async function apiCreatePlace(place) {
  const resp = await fetch(`${API_BASE}/destinations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(place),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to add place");
  return data;
}

async function apiUpdatePlace(id, updates) {
  const resp = await fetch(`${API_BASE}/destinations/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(updates),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to update place");
  return data;
}

async function apiDeletePlace(id) {
  const resp = await fetch(`${API_BASE}/destinations/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to delete place");
  return data;
}

async function apiGetReviews(placeId) {
  const resp = await fetch(`${API_BASE}/destinations/${placeId}/reviews`);
  if (!resp.ok) throw new Error("Failed to load reviews");
  return resp.json();
}

async function apiSubmitReview(placeId, rating, comment) {
  const resp = await fetch(`${API_BASE}/destinations/${placeId}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ rating, comment }),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to submit review");
  return data;
}

async function apiGetRecommendations() {
  const resp = await fetch(`${API_BASE}/recommendations`, { headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to load recommendations");
  return resp.json();
}

async function apiGetItineraries() {
  const resp = await fetch(`${API_BASE}/itineraries`, { headers: authHeaders() });
  if (!resp.ok) throw new Error("Failed to load itineraries");
  return resp.json();
}

async function apiCreateItinerary(itinerary) {
  const resp = await fetch(`${API_BASE}/itineraries`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(itinerary),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to create itinerary");
  return data;
}
async function apiGetAllUsers() {
  const resp = await fetch(`${API_BASE}/users`, { headers: authHeaders() });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to load users");
  return data;
}

async function apiDeleteUser(username) {
  const resp = await fetch(`${API_BASE}/users/${username}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to delete user");
  return data;
}

async function apiGetAllItineraries() {
  const resp = await fetch(`${API_BASE}/itineraries/all`, { headers: authHeaders() });
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || "Failed to load itineraries");
  return data;
}