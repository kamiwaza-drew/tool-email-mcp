import { z } from 'zod';

/**
 * Schema for token response from auth endpoints.
 */
export const TokenResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default('Bearer'),
  expires_in: z.number(),
  refresh_token: z.string().optional(),
});

export type TokenResponse = z.infer<typeof TokenResponseSchema>;

/**
 * Schema for user identity extracted from ForwardAuth headers.
 */
export const IdentitySchema = z.object({
  userId: z.string(),
  email: z.string().optional(),
  name: z.string().optional(),
  roles: z.array(z.string()).default([]),
});

export type Identity = z.infer<typeof IdentitySchema>;
