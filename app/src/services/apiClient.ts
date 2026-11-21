/**
 * Shared HTTP helper for future backend integration.
 * Do not put private keys or secrets in VITE_* environment variables.
 * The backend team should confirm the base URL, auth mechanism and response contract.
 */
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  details: unknown;
  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError('The backend API URL has not been configured yet.', 0);
  }
  const response = await fetch(`${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
    credentials: 'include',
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const message = body && typeof body.message === 'string' ? body.message : 'The request could not be completed.';
    throw new ApiError(message, response.status, body);
  }
  return body as T;
}
