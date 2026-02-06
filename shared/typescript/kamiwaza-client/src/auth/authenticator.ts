/**
 * Interface for client authentication strategies.
 * Mirrors Python SDK's Authenticator abstract class.
 */
export interface Authenticator {
  /**
   * Apply authentication to the given headers.
   * @param headers - Headers object to modify with auth credentials
   */
  authenticate(headers: Headers): Promise<void>;

  /**
   * Refresh the authentication credentials.
   */
  refreshToken(): Promise<void>;

  /**
   * Get the current access token if available.
   */
  getAccessToken(): Promise<string | null>;
}

/**
 * Simple bearer token authenticator backed by a PAT/API key.
 * Mirrors Python SDK's ApiKeyAuthenticator.
 */
export class ApiKeyAuthenticator implements Authenticator {
  private readonly apiKey: string;

  constructor(apiKey: string) {
    this.apiKey = apiKey;
  }

  async authenticate(headers: Headers): Promise<void> {
    headers.set('Authorization', `Bearer ${this.apiKey}`);
  }

  async refreshToken(): Promise<void> {
    // Nothing to refresh for static API keys
  }

  async getAccessToken(): Promise<string | null> {
    return this.apiKey;
  }
}

/**
 * Authenticator that uses pre-extracted ForwardAuth headers.
 * Used in App Garden apps where Traefik has already validated the user.
 */
export class ForwardAuthAuthenticator implements Authenticator {
  private readonly authHeaders: Record<string, string>;

  /**
   * Create a ForwardAuth authenticator from extracted headers.
   * @param authHeaders - Headers extracted via forwardAuthHeaders()
   */
  constructor(authHeaders: Record<string, string>) {
    this.authHeaders = authHeaders;
  }

  async authenticate(headers: Headers): Promise<void> {
    for (const [key, value] of Object.entries(this.authHeaders)) {
      headers.set(key, value);
    }
  }

  async refreshToken(): Promise<void> {
    // ForwardAuth tokens are managed by the upstream auth service
    // Nothing to refresh on our side
  }

  async getAccessToken(): Promise<string | null> {
    const auth = this.authHeaders['authorization'];
    if (auth?.startsWith('Bearer ')) {
      return auth.slice(7);
    }
    return null;
  }
}

/**
 * No-op authenticator for unauthenticated requests.
 */
export class NoAuthAuthenticator implements Authenticator {
  async authenticate(_headers: Headers): Promise<void> {
    // No auth to apply
  }

  async refreshToken(): Promise<void> {
    // Nothing to refresh
  }

  async getAccessToken(): Promise<string | null> {
    return null;
  }
}
