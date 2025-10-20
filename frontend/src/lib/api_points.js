// frontend/src/lib/api_points.js
const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function callGeneratePoints(payload) {
  const res = await fetch(`${BASE}/generate/points`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`Server returned ${res.status}: ${txt}`);
  }
  return res.json();
}
