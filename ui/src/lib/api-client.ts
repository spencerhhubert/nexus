import createClient from 'openapi-fetch';
import type { paths } from './api-types';

export const apiClient = createClient<paths>({
  baseUrl: 'http://localhost:8000',
});

export async function pauseSystem() {
  const { error } = await apiClient.PUT('/pause');
  if (error) throw new Error('Failed to pause system');
}

export async function resumeSystem() {
  const { error } = await apiClient.PUT('/resume');
  if (error) throw new Error('Failed to resume system');
}
