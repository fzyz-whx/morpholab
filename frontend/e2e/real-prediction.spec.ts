import { test, expect } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

// Requires audited source data, real trained checkpoints, the API and a live worker.
// No request interception or synthetic model is used in this project.
test('real NCA job persists, overlays the correct source frame and restores from history', async ({
  page,
}) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/studio/WH01');
  await expect(page.getByRole('img', { name: /WH01 第 0 帧/ })).toBeVisible();
  await page
    .getByRole('group', { name: '工作台检查面板' })
    .getByRole('button', { name: '预测实验', exact: true })
    .click();
  await page.getByRole('combobox', { name: '预测模型' }).selectOption('nca');
  await page.getByRole('spinbutton', { name: '预测步数' }).fill('24');
  const submitted = page.waitForResponse(
    (response) =>
      response.url().endsWith('/api/v1/experiments/predict') &&
      response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: '提交预测实验', exact: true }).click();
  const response = await submitted;
  expect(response.status()).toBe(202);
  const { job } = await response.json();
  await expect(page.locator('[data-job-status="succeeded"]')).toBeVisible({ timeout: 25_000 });
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('4');
  await expect(page.getByRole('img', { name: /WH01 第 4 帧/ })).toBeVisible();
  await page.getByRole('img', { name: /WH01 第 4 帧/ }).hover();
  await expect(page.getByLabel('原始图像坐标')).toHaveText(/X 06[34] \/ Y 06[34]/);
  await page.getByRole('button', { name: '前帧参照', exact: true }).click();
  await expect(page.getByRole('img', { name: 'WH01 前一真实观测帧 3' })).toHaveJSProperty(
    'naturalWidth',
    128,
  );
  await expect(page.getByRole('img', { name: /PREDICTION Lead 1/ })).toBeVisible();
  const result = await page.request.get(`/api/v1/jobs/${job.id}/result`);
  const body = await result.json();
  expect(body.model.seed).toBe(17); // Fixed by validation, not by this sequence's future.
  expect(body.model.checkpoint_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(body.frames).toHaveLength(24);
  expect(body.frames[0].source_frame_index).toBe(4);
  expect(body.frames[23].metrics.iou).toBeGreaterThanOrEqual(0);
  await page.getByRole('button', { name: /派生区域误差/ }).click();
  const errorImage = page.getByRole('img', { name: /误差层.*FP/ });
  await expect(errorImage).toBeVisible();
  await expect(errorImage).toHaveJSProperty('naturalWidth', 64);
  expect(body.frames[0].region).toBeUndefined();
  expect(body.frames[0].images.prediction.url).toContain(`/jobs/${job.id}/frames/1`);
  await fs.mkdir(path.resolve('../artifacts/browser'), { recursive: true });
  await page.screenshot({ path: path.resolve('../artifacts/browser/studio-prediction-1440.png') });
  const viewport = page.getByLabel('影像画布，方向键逐帧，空格播放，Home和End跳转首尾');
  await viewport.focus();
  await viewport.press('End');
  await expect(page.locator('.prediction-overlay')).toHaveCount(0);
  await page.reload();
  await page
    .getByRole('group', { name: '工作台检查面板' })
    .getByRole('button', { name: '预测实验', exact: true })
    .click();
  await page.locator('summary').filter({ hasText: '实验历史' }).click();
  await page.locator('.experiment-history li button').first().click();
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('4');
  await expect(page.locator('.prediction-overlay')).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.getByRole('img', { name: /WH01 第 4 帧/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('.prediction-metrics h3').scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.resolve('../artifacts/browser/studio-prediction-1280.png') });
  expect(errors).toEqual([]);
});

test('real frozen research report exposes all leads and actual seed counts', async ({ page }) => {
  await page.goto('/research');
  await expect(page.getByRole('img', { name: /随 lead 变化/ })).toBeVisible();
  await expect(page.locator('.research-chart [data-model-id]')).toHaveCount(6);
  await expect(page.locator('.research-results').first().locator('tbody tr')).toHaveCount(18);
  await expect(page.locator('.research-run-section tbody tr')).toHaveCount(12);
  await expect(page.locator('.research-failure img')).toHaveCount(6);
  for (const image of await page.locator('.research-failure img').all()) {
    await image.scrollIntoViewIfNeeded();
    await expect(image).toHaveJSProperty('naturalWidth', 1024);
  }
  await page.getByRole('combobox', { name: '研究指标' }).selectOption('mean_boundary_distance');
  await expect(page.getByRole('img', { name: /平均边界距离/ })).toBeVisible();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: path.resolve('../artifacts/browser/research-real-v1.png'),
    fullPage: false,
  });
});

test('mobile can read the project and source metadata with a clear desktop workbench note', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('main h1')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(
    true,
  );
  await page.goto('/datasets');
  await expect(page.locator('tbody tr')).toHaveCount(62);
  await page.goto('/studio/WH01');
  await expect(page.locator('.desktop-workbench-note')).toBeVisible();
});
