import { z } from 'zod';

/**
 * Schema for a model instance within a deployment.
 */
export const InstanceSchema = z.object({
  id: z.string().uuid().optional(),
  host_name: z.string().nullish(),
  status: z.string(),
  port: z.number().optional(),
});

export type Instance = z.infer<typeof InstanceSchema>;

/**
 * Schema for a raw deployment from the API.
 */
export const DeploymentSchema = z.object({
  id: z.string().uuid(),
  m_id: z.string().uuid(),
  m_name: z.string(),
  status: z.string(),
  instances: z.array(InstanceSchema).default([]),
  lb_port: z.number().default(0),
  access_path: z.string().nullish(),
  engine_name: z.string().nullish(),
});

export type Deployment = z.infer<typeof DeploymentSchema>;

/**
 * Schema for an active deployment with computed endpoint.
 */
export const ActiveDeploymentSchema = z.object({
  id: z.string().uuid(),
  m_id: z.string().uuid(),
  m_name: z.string(),
  status: z.string(),
  lb_port: z.number(),
  endpoint: z.string().nullable(),
  instance_count: z.number(),
  engine_name: z.string().nullish(),
});

export type ActiveDeployment = z.infer<typeof ActiveDeploymentSchema>;

/**
 * Schema for creating a deployment.
 */
export const CreateDeploymentRequestSchema = z.object({
  m_id: z.string().uuid(),
  m_config_id: z.string().uuid().optional(),
  m_file_id: z.string().uuid().optional(),
  engine_name: z.string().optional(),
  min_copies: z.number().optional(),
  max_copies: z.number().optional(),
});

export type CreateDeploymentRequest = z.infer<typeof CreateDeploymentRequestSchema>;
