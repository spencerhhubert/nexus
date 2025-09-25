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

export async function runSystem() {
  const { error } = await apiClient.PUT('/run');
  if (error) throw new Error('Failed to run system');
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

export async function getBricklinkPartInfo(partId: string) {
  const { data, error } = await apiClient.GET('/bricklink/part/{part_id}/', {
    params: {
      path: { part_id: partId },
    },
  });
  if (error) throw new Error('Failed to get BrickLink part info');
  return data;
}
