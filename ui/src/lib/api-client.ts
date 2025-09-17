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

export async function getIRLRuntimeParams() {
  const { data, error } = await apiClient.GET('/irl-runtime-params');
  if (error) throw new Error('Failed to get IRL runtime params');
  return data;
}

export async function updateIRLRuntimeParams(params: any) {
  const { error } = await apiClient.PUT('/irl-runtime-params', {
    body: params,
  });
  if (error) throw new Error('Failed to update IRL runtime params');
}
