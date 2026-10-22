import fs from 'node:fs/promises';
import { fileURLToPath, URL } from 'node:url';
import process from 'node:process';
import { log } from 'node:console';
import openapiTS, { astToString } from 'openapi-typescript';
import { format, resolveConfig } from 'prettier';

const destination = new URL('../src/generated/api.d.ts', import.meta.url);
const schema = new URL('../../docs/architecture/openapi.json', import.meta.url);
const ast = await openapiTS(schema);
const source =
  '// Generated from FastAPI OpenAPI. Run pnpm api:generate; do not edit.\n' + astToString(ast);
const text = await format(source, {
  ...(await resolveConfig(fileURLToPath(destination))),
  parser: 'typescript',
});
if (process.argv.includes('--check')) {
  if ((await fs.readFile(destination, 'utf8')) !== text) {
    throw new Error('Generated API types are stale; run pnpm api:generate');
  }
  log('Generated prediction contract matches the committed OpenAPI schema');
} else {
  await fs.mkdir(new URL('../src/generated/', import.meta.url), { recursive: true });
  await fs.writeFile(destination, text);
  log('Generated src/generated/api.d.ts');
}
