import type { KamiwazaClient } from '../client';

/**
 * Base class for all service classes.
 * Mirrors Python SDK's BaseService pattern.
 */
export abstract class BaseService {
  protected readonly client: KamiwazaClient;

  constructor(client: KamiwazaClient) {
    this.client = client;
  }
}
