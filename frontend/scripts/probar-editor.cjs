const { buildSync } = require('esbuild');
const { spawnSync } = require('node:child_process');
const path = require('node:path');

const archivo = path.resolve(__dirname, '../node_modules/.cache/tests/editor-lotes.test.cjs');
buildSync({
  entryPoints: [path.resolve(__dirname, '../tests/editor-lotes.test.tsx')],
  outfile: archivo,
  bundle: true,
  platform: 'node',
  format: 'cjs',
  jsx: 'automatic',
  external: ['react', 'react-dom/*'],
});
const resultado = spawnSync(process.execPath, ['--test', archivo], { stdio: 'inherit' });
if (resultado.error) throw resultado.error;
process.exit(resultado.status ?? 1);
