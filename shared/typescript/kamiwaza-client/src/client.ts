import { APIError, AuthenticationError, ConfigurationError } from './errors';
import type { Authenticator } from './auth/authenticator';
import { ApiKeyAuthenticator, NoAuthAuthenticator } from './auth/authenticator';
import { ServingService } from './services/serving';

/**
 * Configuration options for KamiwazaClient.
 */
export interface KamiwazaClientConfig {
  /**
   * Base URL for the Kamiwaza API.
   * Falls back to KAMIWAZA_API_URL or KAMIWAZA_BASE_URL environment variables.
   */
  baseUrl?: string;

  /**
   * Public URL for constructing model endpoints (browser-accessible).
   * Falls back to KAMIWAZA_PUBLIC_API_URL or baseUrl.
   */
  publicApiUrl?: string;

  /**
   * API key for authentication.
   * Falls back to KAMIWAZA_API_KEY environment variable.
   */
  apiKey?: string;

  /**
   * Custom authenticator instance.
   * Takes precedence over apiKey if provided.
   */
  authenticator?: Authenticator;

  /**
   * Whether to verify SSL certificates.
   * Falls back to KAMIWAZA_VERIFY_SSL environment variable.
   * Note: In browser environments, this is handled by the browser.
   */
  verifySSL?: boolean;
}

/**
 * Options for HTTP requests.
 */
export interface RequestOptions {
  params?: Record<string, string>;
  json?: unknown;
  headers?: Record<string, string>;
  skipAuth?: boolean;
}

/**
 * Resolve base URL from config or environment.
 */
function resolveBaseUrl(configUrl?: string): string {
  const url =
    configUrl ||
    (typeof process !== 'undefined' ? process.env?.KAMIWAZA_API_URL : undefined) ||
    (typeof process !== 'undefined' ? process.env?.KAMIWAZA_BASE_URL : undefined);

  if (!url) {
    throw new ConfigurationError(
      'baseUrl is required. Provide it directly or set KAMIWAZA_API_URL or KAMIWAZA_BASE_URL.'
    );
  }

  return url.replace(/\/+$/, ''); // Remove trailing slashes
}

/**
 * Resolve public API URL for constructing model endpoints.
 */
function resolvePublicApiUrl(configUrl?: string, baseUrl?: string): string {
  const url =
    configUrl ||
    (typeof process !== 'undefined' ? process.env?.KAMIWAZA_PUBLIC_API_URL : undefined) ||
    baseUrl;

  if (!url) {
    throw new ConfigurationError('Could not resolve public API URL');
  }

  return url.replace(/\/+$/, '');
}

/**
 * Create default authenticator from config.
 */
function createDefaultAuthenticator(apiKey?: string): Authenticator {
  const key =
    apiKey ||
    (typeof process !== 'undefined' ? process.env?.KAMIWAZA_API_KEY : undefined) ||
    (typeof process !== 'undefined' ? process.env?.KAMIWAZA_API_TOKEN : undefined);

  if (key) {
    return new ApiKeyAuthenticator(key);
  }

  return new NoAuthAuthenticator();
}

/**
 * Main client for interacting with the Kamiwaza API.
 * Mirrors the Python SDK's KamiwazaClient class.
 *
 * @example
 * ```typescript
 * import { KamiwazaClient } from '@kamiwaza/client';
 *
 * const client = new KamiwazaClient({
 *   baseUrl: 'https://kamiwaza.example.com/api',
 *   apiKey: 'your-api-key',
 * });
 *
 * const deployments = await client.serving.listActiveDeployments();
 * ```
 */
export class KamiwazaClient {
  readonly baseUrl: string;
  private readonly publicApiUrl: string;
  private readonly authenticator: Authenticator;

  // Lazy-loaded services
  private _serving?: ServingService;

  constructor(config: KamiwazaClientConfig = {}) {
    this.baseUrl = resolveBaseUrl(config.baseUrl);
    this.publicApiUrl = resolvePublicApiUrl(config.publicApiUrl, this.baseUrl);
    this.authenticator = config.authenticator ?? createDefaultAuthenticator(config.apiKey);
  }

  /**
   * Get the public base origin for constructing model endpoints.
   */
  getPublicBaseOrigin(): string {
    const url = new URL(this.publicApiUrl);
    return `${url.protocol}//${url.host}`;
  }

  /**
   * Internal method to make HTTP requests.
   */
  private async request<T>(
    method: string,
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<T> {
    const url = new URL(endpoint.replace(/^\/+/, ''), this.baseUrl + '/');

    // Add query params
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        url.searchParams.set(key, value);
      }
    }

    // Build headers
    const headers = new Headers(options.headers);
    if (options.json !== undefined) {
      headers.set('Content-Type', 'application/json');
    }

    // Apply authentication
    if (!options.skipAuth) {
      await this.authenticator.authenticate(headers);
    }

    // Make request
    const response = await fetch(url.toString(), {
      method,
      headers,
      body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
    });

    // Handle 401 - try token refresh
    if (response.status === 401 && !options.skipAuth) {
      try {
        await this.authenticator.refreshToken();
        await this.authenticator.authenticate(headers);

        const retryResponse = await fetch(url.toString(), {
          method,
          headers,
          body: options.json !== undefined ? JSON.stringify(options.json) : undefined,
        });

        if (retryResponse.status === 401) {
          throw new AuthenticationError('Authentication failed after token refresh.');
        }

        return this.handleResponse<T>(retryResponse);
      } catch (error) {
        if (error instanceof AuthenticationError) throw error;
        throw new AuthenticationError('Authentication failed. No valid credentials.');
      }
    }

    return this.handleResponse<T>(response);
  }

  /**
   * Handle API response.
   */
  private async handleResponse<T>(response: Response): Promise<T> {
    if (response.status === 204) {
      return undefined as T;
    }

    const contentType = response.headers.get('content-type') || '';

    if (!response.ok) {
      const text = await response.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        data = undefined;
      }

      throw new APIError(
        `API request failed with status ${response.status}: ${text}`,
        response.status,
        text,
        data
      );
    }

    if (contentType.includes('application/json')) {
      return response.json() as Promise<T>;
    }

    // Return text for non-JSON responses
    return response.text() as unknown as T;
  }

  /**
   * Make a GET request.
   */
  async get<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('GET', endpoint, options);
  }

  /**
   * Make a POST request.
   */
  async post<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('POST', endpoint, options);
  }

  /**
   * Make a PUT request.
   */
  async put<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('PUT', endpoint, options);
  }

  /**
   * Make a DELETE request.
   */
  async delete<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('DELETE', endpoint, options);
  }

  /**
   * Make a PATCH request.
   */
  async patch<T>(endpoint: string, options?: RequestOptions): Promise<T> {
    return this.request<T>('PATCH', endpoint, options);
  }

  /**
   * Get the current access token if available.
   */
  async getBearerToken(): Promise<string | null> {
    return this.authenticator.getAccessToken();
  }

  // ============================================
  // Service Properties (lazy-loaded)
  // ============================================

  /**
   * Service for managing model deployments.
   */
  get serving(): ServingService {
    if (!this._serving) {
      this._serving = new ServingService(this);
    }
    return this._serving;
  }
}
