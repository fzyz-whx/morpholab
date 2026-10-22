import { useQuery } from '@tanstack/react-query';
import { request } from './api';

import type { components } from './generated/api';

export type ModelRecord = components['schemas']['RegisteredModel'];
export type PredictionRequest = components['schemas']['PredictionRequest'];
export type PredictionJob = components['schemas']['PredictionJob'];
export type JobStatus = PredictionJob['status'];
export type LeadMetrics = components['schemas']['LeadMetrics'];
export type PredictedFrame = components['schemas']['PredictionFrame'];
export type PredictionResult = components['schemas']['PredictionResult'];

export const jobStatusLabels: Record<JobStatus, string> = {
  queued: '排队中',
  running: '运行中',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已取消',
};
export const isActiveJob = (status?: JobStatus) => status === 'queued' || status === 'running';
export function useModels() {
  return useQuery({
    queryKey: ['models'],
    queryFn: async ({ signal }) =>
      (await request<{ items: ModelRecord[] }>('/models', signal)).items ?? [],
  });
}
export function useExperiments() {
  return useQuery({
    queryKey: ['experiments'],
    queryFn: async ({ signal }) =>
      (await request<{ items: PredictionJob[] }>('/experiments', signal)).items ?? [],
    refetchInterval: (query) =>
      query.state.data?.some((job) => isActiveJob(job.status)) ? 1000 : false,
  });
}
export function postPrediction<T>(path: string, body?: unknown) {
  return request<T>(path, undefined, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
}
