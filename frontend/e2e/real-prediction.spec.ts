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
  await expect(page.getByRole('img', { name: /PREDICTION Lead 1/ })).toBeVisible();
  const result = await page.request.get(`/api/v1/jobs/${job.id}/result`);
  const body = await result.json();
  expect(body.model.seed).toBe(17); // Fixed by validation, not by this sequence's future.
  expect(body.model.checkpoint_sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(body.frames).toHaveLength(24);
  expect(body.frames[0].source_frame_index).toBe(4);
  expect(body.frames[23].metrics.iou).toBeGreaterThanOrEqual(0);
  await page.getByRole('button', { name: /派生区域误差/ }).click();
  expect(await page.locator('.prediction-overlay rect').count()).toBeGreaterThan(0);
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
  await expect(page.locator('.research-results tbody tr')).toHaveCount(18);
  await page.getByRole('combobox', { name: '研究指标' }).selectOption('mean_boundary_distance');
  await expect(page.getByRole('img', { name: /平均边界距离/ })).toBeVisible();
  await page.screenshot({
    path: path.resolve('../artifacts/browser/research-real-v1.png'),
    fullPage: false,
  });
});
