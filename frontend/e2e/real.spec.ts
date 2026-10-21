import { test, expect } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs/promises';

const screenshots = path.resolve('../artifacts/browser');

test('real archive opens an observed sequence with original annotation', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  await page.goto('/datasets');
  await expect(page.locator('tbody tr')).toHaveCount(62);
  await page.getByRole('textbox', { name: '搜索序列' }).fill('WH01');
  await expect(page.locator('tbody tr')).toHaveCount(1);
  await page.getByRole('link', { name: 'WH01', exact: true }).click();
  const image = page.getByRole('img', { name: /WH01 第 0 帧/ });
  await expect(image).toBeVisible();
  await expect(image).toHaveJSProperty('naturalWidth', 128);
  await expect(page.getByText('轮廓 QC 通过', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: /真实观测/ }).click();
  await expect(image).toHaveAttribute('src', /layer=observed/);
  await expect(image).toBeVisible();
  await page.getByRole('button', { name: /原始注释/ }).click();
  await expect(page.getByRole('img', { name: /WH01 第 0 帧/ })).toHaveAttribute(
    'src',
    /layer=annotation/,
  );
  await page.getByRole('button', { name: /轮廓叠加/ }).click();
  await expect(page.getByRole('img', { name: /WH01 第 0 帧/ })).toBeVisible();
  expect(errors).toEqual([]);
});

test('real timeline supports keys, playback, original ordering and failed QC', async ({ page }) => {
  await page.goto('/studio/WH01');
  const range = page.getByRole('slider', { name: '选择帧' });
  await expect(range).toHaveValue('0');
  await page.getByRole('button', { name: '下一帧', exact: true }).click();
  await expect(range).toHaveValue('1');
  const viewport = page.getByLabel('影像画布，方向键逐帧，空格播放，Home和End跳转首尾');
  await viewport.focus();
  await viewport.press('End');
  await expect(range).toHaveValue('121');
  await expect(page.getByRole('button', { name: '下一帧', exact: true })).toBeDisabled();
  await viewport.press('Home');
  await viewport.press('Space');
  await expect.poll(() => range.inputValue()).not.toBe('0');
  await viewport.press('Space');
  await page.goto('/studio/WHu07');
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('0');
  await page.getByLabel('影像画布，方向键逐帧，空格播放，Home和End跳转首尾').press('End');
  await expect(page.getByRole('slider', { name: '选择帧' })).toHaveValue('158');
  await expect(page.getByText('轮廓 QC 未通过', { exact: true })).toBeVisible();
  await expect(page.getByRole('img', { name: /WHu07 第 158 帧/ })).toBeVisible();
});

test('actual desktop screenshots have a loaded frame and no page overflow', async ({ page }) => {
  await fs.mkdir(screenshots, { recursive: true });
  await page.goto('/');
  await expect(page.getByRole('img')).toHaveJSProperty('naturalWidth', 128);
  await page.screenshot({ path: path.join(screenshots, 'overview-1440.png'), fullPage: true });
  await page.goto('/datasets');
  await expect(page.locator('tbody tr')).toHaveCount(62);
  await page.screenshot({ path: path.join(screenshots, 'archive-1440.png') });
  for (const [width, height] of [
    [1440, 900],
    [1280, 720],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto('/studio/WH01');
    const image = page.getByRole('img', { name: /WH01 第 0 帧/ });
    const viewport = page.getByLabel('影像画布，方向键逐帧，空格播放，Home和End跳转首尾');
    await expect(image).toBeVisible();
    await expect
      .poll(async () =>
        image.evaluate((element) => {
          const imageRect = element.getBoundingClientRect();
          const viewportRect = element.closest('.scientific-viewport')!.getBoundingClientRect();
          return (
            imageRect.top >= viewportRect.top &&
            imageRect.bottom <= viewportRect.bottom &&
            imageRect.left >= viewportRect.left &&
            imageRect.right <= viewportRect.right &&
            Math.abs(imageRect.width / imageRect.height - 1) < 0.01
          );
        }),
      )
      .toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(
      true,
    );
    await page.screenshot({ path: path.join(screenshots, `studio-${width}.png`) });
    await page.getByRole('slider', { name: '画布缩放' }).focus();
    await page.getByRole('slider', { name: '画布缩放' }).press('End');
    expect(await viewport.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(
      true,
    );
    await page.getByRole('button', { name: '适合画布', exact: true }).click();
    await expect.poll(() => viewport.evaluate((element) => element.scrollTop)).toBe(0);
  }
});
