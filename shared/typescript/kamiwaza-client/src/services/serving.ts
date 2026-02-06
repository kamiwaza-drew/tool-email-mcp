import { BaseService } from './base';
import {
  DeploymentSchema,
  ActiveDeploymentSchema,
  type Deployment,
  type ActiveDeployment,
  type CreateDeploymentRequest,
} from '../schemas/serving';

/**
 * Service for managing model deployments.
 * Mirrors Python SDK's ServingService.
 */
export class ServingService extends BaseService {
  /**
   * List all model deployments.
   * @param modelId - Optional filter by model ID
   */
  async listDeployments(modelId?: string): Promise<Deployment[]> {
    const params = modelId ? { model_id: modelId } : undefined;
    const response = await this.client.get<unknown[]>('/serving/deployments', { params });
    return response.map(item => DeploymentSchema.parse(item));
  }

  /**
   * List active deployments with computed endpoints.
   * Mirrors Python SDK's list_active_deployments().
   */
  async listActiveDeployments(): Promise<ActiveDeployment[]> {
    const deployments = await this.listDeployments();
    const active: ActiveDeployment[] = [];

    // Get base origin for constructing endpoints
    const baseOrigin = this.client.getPublicBaseOrigin();

    for (const deployment of deployments) {
      // Skip non-deployed
      if (deployment.status !== 'DEPLOYED') continue;

      // Check for running instances
      const runningInstances = deployment.instances.filter(i => i.status === 'DEPLOYED');
      if (runningInstances.length === 0) continue;

      // Build endpoint URL
      let endpoint: string | null = null;
      if (deployment.access_path) {
        // Path-based routing (preferred)
        endpoint = `${baseOrigin}${deployment.access_path}/v1`;
      } else if (deployment.lb_port) {
        // Port-based routing (fallback)
        const url = new URL(baseOrigin);
        endpoint = `${url.protocol}//${url.hostname}:${deployment.lb_port}/v1`;
      }

      active.push(
        ActiveDeploymentSchema.parse({
          id: deployment.id,
          m_id: deployment.m_id,
          m_name: deployment.m_name,
          status: deployment.status,
          lb_port: deployment.lb_port,
          endpoint,
          instance_count: runningInstances.length,
          engine_name: deployment.engine_name,
        })
      );
    }

    return active;
  }

  /**
   * Get a specific deployment by ID.
   * @param deploymentId - The deployment UUID
   */
  async getDeployment(deploymentId: string): Promise<Deployment> {
    const response = await this.client.get<unknown>(`/serving/deployment/${deploymentId}`);
    return DeploymentSchema.parse(response);
  }

  /**
   * Deploy a model.
   * @param request - Deployment configuration
   * @returns The new deployment ID
   */
  async deployModel(request: CreateDeploymentRequest): Promise<string> {
    const response = await this.client.post<string>('/serving/deploy_model', {
      json: {
        m_id: request.m_id,
        m_config_id: request.m_config_id,
        m_file_id: request.m_file_id,
        engine_name: request.engine_name,
        min_copies: request.min_copies,
        max_copies: request.max_copies,
      },
    });
    return response;
  }

  /**
   * Stop a deployment.
   * @param deploymentId - The deployment UUID
   * @param force - Force stop even if in use
   */
  async stopDeployment(deploymentId: string, force = false): Promise<void> {
    await this.client.delete(`/serving/deployment/${deploymentId}`, {
      params: { force: String(force) },
    });
  }

  /**
   * Get deployment status.
   * @param deploymentId - The deployment UUID
   */
  async getDeploymentStatus(deploymentId: string): Promise<Deployment> {
    const response = await this.client.get<unknown>(`/serving/deployment/${deploymentId}/status`);
    return DeploymentSchema.parse(response);
  }

  /**
   * Get serving health status.
   */
  async getHealth(): Promise<unknown[]> {
    return this.client.get<unknown[]>('/serving/health');
  }
}
