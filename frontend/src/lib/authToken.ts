let currentAuthToken: string | null = null;

export function getAuthToken(): string | null {
  return currentAuthToken;
}

export function setAuthToken(token: string | null): void {
  currentAuthToken = token;
}