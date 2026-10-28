/**
 * API client wrapper for VeriHire v2
 * Reads VITE_API_URL, attaches Bearer token, and handles 401 session expiry.
 */

export class ApiError extends Error {
  status: number;
  detail?: any;
  data?: any;

  constructor(message: string, status: number, detail?: any, data?: any) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem("verihire_token");
  } catch {
    return null;
  }
}

export function setStoredToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem("verihire_token", token);
    } else {
      localStorage.removeItem("verihire_token");
    }
  } catch {
    // Ignore localStorage access failures (e.g. private browsing storage disabled)
  }
}

export const API_BASE_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
  const headers = new Headers(options.headers || {});

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getStoredToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // If unauthorized and not an authentication request, clear token and redirect
    if (!endpoint.includes("/auth/login") && !endpoint.includes("/auth/register")) {
      setStoredToken(null);
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
  }

  let data: any = null;
  const contentType = res.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    const detail = data?.detail;
    let message = `Request failed with status ${res.status}`;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
    } else if (typeof detail === "object" && detail !== null) {
      message = detail.message || JSON.stringify(detail);
    } else if (typeof data?.message === "string") {
      message = data.message;
    }
    throw new ApiError(message, res.status, detail, data);
  }

  return data as T;
}
