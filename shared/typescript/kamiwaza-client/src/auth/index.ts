// Auth module exports
export { forwardAuthHeaders, extractIdentity } from './headers';
export {
  type Authenticator,
  ApiKeyAuthenticator,
  ForwardAuthAuthenticator,
  NoAuthAuthenticator,
} from './authenticator';
