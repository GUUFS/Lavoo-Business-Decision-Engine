// src/utils/fetchHelper.ts
import Cookies from "js-cookie";

const BASE_URL = import.meta.env.VITE_APP_API_BASE_URL || "http://localhost:8000"; // ✅ Use environment variable

export async function fetchHelper<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = Cookies.get("access_token");

  const headers = {
    "Content-Type": "application/json",
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  };

  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    const message = errorBody.detail || `Request failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}