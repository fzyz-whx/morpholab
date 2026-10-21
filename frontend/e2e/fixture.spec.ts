import { test, expect } from '@playwright/test';

// These browser regressions use explicitly synthetic HTTP fixtures. They do not
// validate the real dataset, API implementation, model or scientific results.
const datasetId = 'drosophila_wound_zenodo_7660424';
const tinySyntheticPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aYyoAAAAASUVORK5CYII=',
  'base64',
);

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url());
    const sequence = {
      id: 'SYN001',
      dataset_id: datasetId,
      frame_count: 3,
      width: 128,
      height: 128,
      project_split: 'train',
      official_split: null,
      qc_valid_count: 2,
      qc_definition: 'SYNTHETIC fixture only',
    };
    if (url.pathname.includes('/frames/')) {
      await route.fulfill({
        contentType: 'image/png',
        body: tinySyntheticPng,
        headers: { 'X-Provenance': 'SYNTHETIC' },
      });
    } else if (url.pathname === '/api/v1/datasets') {
      await route.fulfill({
        json: {
          schema_version: '1',
          items: [
            {
              id: datasetId,
              name: 'SYNTHETIC browser fixture',
              biology_domain: 'synthetic_test',
              source_url: 'https://example.invalid/synthetic',
              doi: null,
              license: 'SYNTHETIC',
              sequence_count: 1,
              frame_count: 3,
              local_available: true,
              annotation_type: 'synthetic_boundary',
              model_status: 'untrained',
            },
          ],
        },
      });
    } else if (url.pathname === '/api/v1/sequences') {
      await route.fulfill({ json: { schema_version: '1', items: [sequence] } });
    } else {
      await route.fulfill({
        json: {
          schema_version: '1',
          ...sequence,
          frames: [0, 1, 2].map((frame_index) => ({
            frame_index,
            timestamp_min: null,
            qc_valid: frame_index !== 1,
            touches_border: false,
          })),
        },
      });
    }
  });
});

test('synthetic browser regression covers filters, frame controls and QC state', async ({
  page,
}) => {
  await page.goto('/datasets');
  await expect(page.getByText('SYNTHETIC browser fixture', { exact: true })).toBeVisible();
  await page.getByRole('textbox', { name: '搜索序列' }).fill('missing');
  await expect(page.getByText('没有匹配的序列')).toBeVisible();
  await page.getByRole('button', { name: '清除筛选' }).click();
  await page.getByRole('link', { name: 'SYN001', exact: true }).click();
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('0');
  await page.getByRole('button', { name: '下一帧', exact: true }).click();
  await expect(page.getByText('轮廓 QC 未通过', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '末帧', exact: true }).click();
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('2');
  await expect(page.getByRole('button', { name: '下一帧', exact: true })).toBeDisabled();
});
