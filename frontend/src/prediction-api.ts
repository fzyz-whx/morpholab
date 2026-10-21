import { useQuery } from '@tanstack/react-query';
import { request } from './api';

export interface ModelRecord {
  id: string;
  label: string;
  kind: string;
  variant: string | null;
  seed: number | null;
  trained: boolean;
  available: boolean;
  selection?: { criterion: string; loss: number | null; step: number | null } | null;
  checkpoint_sha256?: string | null;
}
export interface PredictionRequest {
  dataset_id: string;
  sequence_id: string;
  model_id: string;
  observation_start: number;
  observations: number;
  horizon: number;
}
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
export interface PredictionJob {
  id: string;
  status: JobStatus;
  request: PredictionRequest;
  created_at_utc: string;
  updated_at_utc: string;
  cancel_requested: boolean;
  error: string | { message?: string } | null;
  result_available: boolean;
}
export interface LeadMetrics {
  iou: number | null;
  dice: number | null;
  area_mae: number | null;
  signed_area_error: number | null;
  mean_boundary_distance: number | null;
  hausdorff95: number | null;
  empty_boundary_mismatch: boolean | null;
}
export interface PredictedFrame {
  lead: number;
  source_frame_index: number;
  contours: number[][][];
  region: number[][];
  target_region: number[][] | null;
  region_area: number;
  target_valid: boolean;
  metrics: LeadMetrics | null;
}
export interface PredictionResult {
  job_id: string;
  status: 'succeeded';
  request: PredictionRequest;
  grid: { width: number; height: number };
  frames: PredictedFrame[];
  source: {
    source_id: string;
    sequence_id: string;
    archive_sha256: string | null;
    manifest_sha256: string | null;
    npz_sha256: string | null;
    original_width: number;
    original_height: number;
    project_split: string | null;
  };
  model: ModelRecord;
  provenance: string;
  [key: string]: unknown;
}
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
