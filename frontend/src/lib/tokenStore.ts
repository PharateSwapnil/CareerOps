// Access token lives only in memory (never localStorage) - it's short-lived
// and this avoids leaving a usable bearer credential sitting in persistent
// storage. The refresh token is longer-lived and IS persisted, so a page
// reload doesn't force a re-login; that's the standard tradeoff for this
// access+refresh token pattern.
const REFRESH_TOKEN_KEY = "careerops-refresh-token";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getRefreshToken(): string | null {
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string | null): void {
  if (token) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearTokens(): void {
  accessToken = null;
  setRefreshToken(null);
}
