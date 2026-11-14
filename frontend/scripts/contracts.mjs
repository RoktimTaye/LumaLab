import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const result = spawnSync('uv', ['run', '--locked', '--offline', '--cache-dir', '.uv-cache', 'python', '-m', 'scripts.contracts', ...process.argv.slice(2)], {
  cwd: fileURLToPath(new URL('../../backend/', import.meta.url)), stdio: 'inherit', timeout: 30000,
})
if (result.error) console.error('Contract command failed. Install uv and run uv sync --locked in backend/.')
process.exitCode = result.status ?? 1
