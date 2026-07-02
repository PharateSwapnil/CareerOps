import { clearTokens, getAccessToken, getRefreshToken, setAccessToken } from "./tokenStore";

// Dispatched when a request fails auth even after attempting a refresh -
// AuthProvider listens for this to update its state and send the user to
// the login page, without apiFetch needing to import React/router itself.
export const AUTH_LOST_EVENT = "careerops:auth-lost";

async function doRefresh(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const res = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) return false;

  const data = await res.json();
  setAccessToken(data.access_token);
  return true;
}

/**
 * Drop-in replacement for `fetch` that attaches the current access token
 * and, on a 401, attempts exactly one silent token refresh + retry before
 * giving up and signaling that the session is lost.
 */
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const attempt = async (): Promise<Response> => {
    const token = getAccessToken();
    const headers = new Headers(options.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(url, { ...options, headers });
  };

  let response = await attempt();

  if (response.status === 401) {
    const refreshed = await doRefresh();
    if (refreshed) {
      response = await attempt();
    } else {
      clearTokens();
      window.dispatchEvent(new Event(AUTH_LOST_EVENT));
    }
  }

  return response;
}
