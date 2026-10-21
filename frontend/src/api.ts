import { useQuery } from '@tanstack/react-query';

export interface Dataset {
  id: string;
  name: string;
  biology_domain: string;
  source_url: string;
  doi: string | null;
  license: string | null;
  sequence_count: number | null;
  frame_count: number | null;
  local_available: boolean;
  annotation_type: string;
  model_status: string;
}
export interface Sequence {
  id: string;
  dataset_id: string;
  frame_count: number;
  width: number;
  height: number;
  project_split: string | null;
  official_split: string | null;
  qc_valid_count: number;
  qc_definition?: string;
}
export interface Frame {
  frame_index: number;
  timestamp_min: number | null;
  qc_valid: boolean;
  touches_border: boolean;
}
export interface SequenceDetail extends Sequence {
  frames: Frame[];
}
export type Layer = 'observed' | 'annotation' | 'overlay';
export const PRIMARY_DATASET = 'drosophila_wound_zenodo_7660424';

export async function request<T>(
  path: string,
  signal?: AbortSignal,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, { ...init, signal });
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);
    const message =
      body && typeof body === 'object' && 'error' in body
        ? (body as { error?: { message?: string } }).error?.message
        : null;
    throw new Error(message || `数据服务返回 ${response.status}，请检查本地 API。`);
  }
  return response.json() as Promise<T>;
}
export function useDatasets() {
  return useQuery({
    queryKey: ['datasets'],
    queryFn: async ({ signal }) => (await request<{ items: Dataset[] }>('/datasets', signal)).items,
  });
}
export function useSequences(datasetId = PRIMARY_DATASET) {
  return useQuery({
    queryKey: ['sequences', datasetId],
    queryFn: async ({ signal }) =>
      (
        await request<{ items: Sequence[] }>(
          `/sequences?dataset_id=${encodeURIComponent(datasetId)}`,
          signal,
        )
      ).items,
    enabled: Boolean(datasetId),
  });
}
export function useSequence(id: string) {
  return useQuery({
    queryKey: ['sequence', id],
    queryFn: ({ signal }) =>
      request<SequenceDetail>(`/sequences/${encodeURIComponent(id)}`, signal),
    enabled: Boolean(id),
  });
}
export const frameUrl = (id: string, index: number, layer: Layer) =>
  `/api/v1/sequences/${encodeURIComponent(id)}/frames/${index}?layer=${layer}`;
export const splitLabel = (split: string | null) =>
  ({ train: '训练集', validation: '验证集', val: '验证集', test: '留出集', holdout: '留出集' })[
    split ?? ''
  ] ?? '未分配';
