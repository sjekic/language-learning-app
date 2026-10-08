const assert = require('node:assert/strict');
const test = require('node:test');
const { checkDocker } = require('./docker-preflight.cjs');

function checkWith(results) {
  const calls = [];
  const messages = [];
  const status = checkDocker({
    run(command, args) {
      calls.push([command, ...args]);
      assert.ok(results.length, 'Unexpected Docker command');
      return results.shift();
    },
    log(message) { messages.push(message); },
    error(message) { messages.push(message); },
  });
  return { status, calls, output: messages.join('\n') };
}

test('reports a missing Docker CLI before trying Compose', () => {
  const result = checkWith([{ error: Object.assign(new Error('spawn docker ENOENT'), { code: 'ENOENT' }) }]);
  assert.equal(result.status, 1);
  assert.match(result.output, /Docker CLI.*not found/i);
  assert.equal(result.calls.length, 1);
});

test('preserves a missing engine error and explains how to start Docker Desktop', () => {
  const detail = 'open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.';
  const result = checkWith([{ status: 7, stderr: detail, stdout: '' }]);
  assert.equal(result.status, 7);
  assert.ok(result.output.includes(detail));
  assert.match(result.output, /Start Docker Desktop/);
  assert.equal(result.calls.length, 1);
});

test('preserves permission failures without claiming the engine is stopped', () => {
  const detail = 'permission denied while trying to connect to the Docker daemon socket';
  const result = checkWith([{ status: 1, stderr: detail, stdout: '' }]);
  assert.ok(result.output.includes(detail));
  assert.match(result.output, /permission/i);
  assert.doesNotMatch(result.output, /engine is not running/i);
});

test('requires Linux containers for the repository images', () => {
  const result = checkWith([{ status: 0, stdout: 'windows\n', stderr: '' }]);
  assert.equal(result.status, 1);
  assert.match(result.output, /Linux containers/);
  assert.equal(result.calls.length, 1);
});

test('reports a missing Compose plugin after the engine check succeeds', () => {
  const detail = "docker: 'compose' is not a docker command.";
  const result = checkWith([
    { status: 0, stdout: 'linux\n', stderr: '' },
    { status: 1, stdout: '', stderr: detail },
  ]);
  assert.equal(result.status, 1);
  assert.ok(result.output.includes(detail));
  assert.match(result.output, /Compose plugin/);
});

test('passes for a Linux engine with Compose without starting containers', () => {
  const result = checkWith([
    { status: 0, stdout: 'linux\n', stderr: '' },
    { status: 0, stdout: '2.39.1\n', stderr: '' },
  ]);
  assert.equal(result.status, 0);
  assert.deepEqual(result.calls, [
    ['docker', 'info', '--format', '{{.OSType}}'],
    ['docker', 'compose', 'version', '--short'],
  ]);
});

test('turns a hung daemon check into a bounded failure with its original error', () => {
  const result = checkWith([{ error: Object.assign(new Error('spawnSync docker ETIMEDOUT'), { code: 'ETIMEDOUT' }), status: null }]);
  assert.equal(result.status, 1);
  assert.match(result.output, /ETIMEDOUT/);
  assert.match(result.output, /timed out/i);
});
