/**
 * Base error class for Kamiwaza SDK errors.
 */
export class KamiwazaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'KamiwazaError';
  }
}

/**
 * Error thrown when an API request fails.
 */
export class APIError extends KamiwazaError {
  readonly statusCode: number;
  readonly responseText?: string;
  readonly responseData?: unknown;

  constructor(
    message: string,
    statusCode: number,
    responseText?: string,
    responseData?: unknown
  ) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.responseText = responseText;
    this.responseData = responseData;
  }
}

/**
 * Error thrown when authentication fails.
 */
export class AuthenticationError extends KamiwazaError {
  constructor(message: string) {
    super(message);
    this.name = 'AuthenticationError';
  }
}

/**
 * Error thrown when configuration is invalid.
 */
export class ConfigurationError extends KamiwazaError {
  constructor(message: string) {
    super(message);
    this.name = 'ConfigurationError';
  }
}
