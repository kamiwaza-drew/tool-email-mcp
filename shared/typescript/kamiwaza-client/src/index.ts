/**
 * @kamiwaza/client - Kamiwaza TypeScript SDK
 *
 * This is the main entry point for the SDK, suitable for most environments.
 * For server-specific exports, use '@kamiwaza/client/server'.
 */

// Main client
export { KamiwazaClient, type KamiwazaClientConfig, type RequestOptions } from './client';

// Errors
export { KamiwazaError, APIError, AuthenticationError, ConfigurationError } from './errors';

// Auth utilities
export {
  forwardAuthHeaders,
  extractIdentity,
  type Authenticator,
  ApiKeyAuthenticator,
  ForwardAuthAuthenticator,
  NoAuthAuthenticator,
} from './auth';

// Schemas and types
export type {
  Deployment,
  ActiveDeployment,
  CreateDeploymentRequest,
  Instance,
} from './schemas/serving';

export type { TokenResponse, Identity } from './schemas/auth';
