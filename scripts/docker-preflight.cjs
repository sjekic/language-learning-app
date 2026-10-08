const { spawnSync } = require('node:child_process');

function checkDocker({ run = spawnSync, log = console.log, error = console.error } = {}) {
  const options = { encoding: 'utf8', timeout: 10000, windowsHide: true };

  function reportFailure(result, message) {
    error(message);
    if (result.error) error(result.error.message);
    if (result.stderr) error(result.stderr.trimEnd());
    if (result.stdout) error(result.stdout.trimEnd());
    return Number.isInteger(result.status) && result.status > 0 ? result.status : 1;
  }

  const engine = run('docker', ['info', '--format', '{{.OSType}}'], options);
  if (engine.error || engine.status !== 0) {
    const status = reportFailure(engine, 'Docker engine check failed.');
    if (engine.error?.code === 'ENOENT') {
      error('Docker CLI was not found. Install Docker Desktop (or Docker Engine with the Compose plugin), then reopen your terminal.');
    } else if (engine.error?.code === 'ETIMEDOUT') {
      error('Docker did not respond within 10 seconds; the check timed out. Check Docker Desktop or your Docker daemon.');
    } else {
      const details = `${engine.stderr || ''}\n${engine.stdout || ''}`;
      if (/permission denied|access is denied/i.test(details)) {
        error('Check your Docker socket permissions and selected context with: docker context show');
      } else if (/dockerDesktopLinuxEngine|cannot connect|is the docker daemon running|connection refused/i.test(details)) {
        error('Start Docker Desktop and wait until the engine is running. On Windows, select Linux containers.');
        error('If it still fails, check the selected engine with: docker context show');
      } else {
        error('Check Docker Desktop or your Docker daemon, the selected context, and any DOCKER_HOST override.');
      }
    }
    return status;
  }

  if (engine.stdout.trim() !== 'linux') {
    error('This project requires Linux containers. Switch Docker Desktop to Linux containers and retry.');
    return 1;
  }

  const compose = run('docker', ['compose', 'version', '--short'], options);
  if (compose.error || compose.status !== 0) {
    return reportFailure(compose, 'Docker Compose plugin check failed. Install or update the Compose plugin (included in Docker Desktop).');
  }

  log('Docker Linux engine and Compose are ready.');
  return 0;
}

module.exports = { checkDocker };

if (require.main === module) {
  process.exitCode = checkDocker();
}
