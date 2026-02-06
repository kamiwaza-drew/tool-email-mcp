import type { Identity } from '../schemas/auth';

/**
 * Extract auth headers to forward to Kamiwaza API.
 * Mirrors the Python forward_auth_headers() function from KamiwazaClient.
 *
 * @param requestHeaders - The incoming request headers
 * @returns A record of headers to forward to Kamiwaza API
 */
export function forwardAuthHeaders(requestHeaders: Headers): Record<string, string> {
  const forwarded: Record<string, string> = {};

  // Core auth headers
  for (const key of ['authorization', 'cookie']) {
    const value = requestHeaders.get(key);
    if (value) forwarded[key] = value;
  }

  // Forwarded headers (for proper routing and logging)
  const forwardedKeys = [
    'x-forwarded-for',
    'x-forwarded-proto',
    'x-forwarded-host',
    'x-forwarded-uri',
    'x-forwarded-prefix',
    'x-real-ip',
    'x-original-url',
    'x-request-id',
  ];
  for (const key of forwardedKeys) {
    const value = requestHeaders.get(key);
    if (value) forwarded[key] = value;
  }

  // User identity headers (set by Kamiwaza forward auth)
  requestHeaders.forEach((value, key) => {
    if (key.toLowerCase().startsWith('x-user-') && value) {
      forwarded[key.toLowerCase()] = value;
    }
  });

  // Convert access_token cookie to Authorization header if needed
  if (!forwarded['authorization']) {
    const cookieValue = requestHeaders.get('cookie') || '';
    if (cookieValue.includes('access_token=')) {
      for (const part of cookieValue.split(';')) {
        const trimmed = part.trim();
        if (trimmed.startsWith('access_token=')) {
          const token = trimmed.slice('access_token='.length);
          forwarded['authorization'] = `Bearer ${token}`;
          break;
        }
      }
    }
  }

  return forwarded;
}

/**
 * Extract user identity from ForwardAuth headers.
 *
 * @param headers - The request headers containing ForwardAuth identity
 * @returns The extracted identity or null if not present
 */
export function extractIdentity(headers: Headers): Identity | null {
  const userId = headers.get('x-user-id');
  if (!userId) return null;

  const rolesHeader = headers.get('x-user-roles');
  const roles = rolesHeader ? rolesHeader.split(',').map(r => r.trim()) : [];

  return {
    userId,
    email: headers.get('x-user-email') || undefined,
    name: headers.get('x-user-name') || undefined,
    roles,
  };
}
