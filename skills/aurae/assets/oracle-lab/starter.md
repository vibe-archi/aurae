# Oracle Lab starter source

Read [the optional Lab contract](../../references/oracle-lab.md) and [the catalog contract](../../references/oracle-catalog.md) before using this source. This is a reference starter, not an instruction to create a dashboard or install a runtime.

## Materialization

Each marked block below is one file relative to the approved Oracle root (default `oracle-tests/`). Copy the four `harnesses/lab/` files when a dashboard is explicitly requested. Copy the two example scenarios only into an isolated demonstration/qualification catalog, or when explicitly wanted; never treat them as product coverage. Preserve existing project files and adapt the mapping rather than overwrite them.

Use an already available Python 3.10+ runtime, with no third-party dependency. From the project root:

```text
python oracle-tests/harnesses/lab/server.py --project-root . --port 8765
```

Ensure `/.scratchpad/` is explicitly ignored first. The server scans `oracle-tests/scenarios/**/oracle.json`; exact relative layout matters for this reference. Map other approved roots explicitly when adapting. Reports are local in `.scratchpad/oracle-lab/runs/<session>/report.json`; no server restart history is loaded, and rerunning a test replaces its latest visible result. Refreshing does not run tests. A changed descriptor/script/baseline marks retained results as an earlier definition. Local file hashes bind observations, not authority or a sandbox.

The catalog accepts v1 descriptors, direct Python entry points and typed exact JSON comparisons. It does not invoke agents, install packages, execute arbitrary HTTP commands, change baselines or accept a delivery. Project tests still need their own permission, isolation, cleanup and meaningful assertions. The direct-process timeout/cancel path does not qualify child process trees; adapt and test that capability before running such scenarios. Stop with Ctrl+C in the server terminal.

The interface retains the reviewed low-load layout, grouped categories, manual steps, navigation priority, last/earlier run distinction, and Show terminal / Hide terminal with results below. Do not reintroduce permanent instruction cards when adapting it. Qualify on the target OS/runtime; the packaged reference has local Windows qualification, not a cross-platform assurance claim.

## Source files

### harnesses/lab/server.py

<!-- oracle-lab-file: harnesses/lab/server.py -->
```python
"""Oracle Lab local starter. Standard library; registered tests run with operator permissions."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT.parent.parent
SCENARIOS = CATALOG / 'scenarios'
DISCLAIMER = 'Local test observations, not an assurance decision. Fictional examples do not qualify a product.'
CREATION_FLAGS = getattr(subprocess, 'CREATE_NO_WINDOW', 0)


def now():
    return datetime.now(timezone.utc).isoformat()


def project_info(path):
    info = {'name': path.name, 'path': str(path), 'git': False, 'branch': None,
            'commit': None, 'dirty': None, 'notice': '', 'checked_at': now()}
    def git(*args):
        return subprocess.run(['git', '-C', str(path), *args], capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=5,
                              creationflags=CREATION_FLAGS)
    try:
        probe = git('rev-parse', '--show-toplevel')
        if probe.returncode:
            info['notice'] = ('The .git folder exists, but Git does not recognize a valid repository.'
                              if (path / '.git').exists() else 'No Git repository was recognized in this folder.')
            return info
        info['git'] = True
        info['repository_root'] = probe.stdout.strip()
        branch = git('symbolic-ref', '--quiet', '--short', 'HEAD')
        commit = git('rev-parse', '--verify', 'HEAD')
        info['branch'] = branch.stdout.strip() if branch.returncode == 0 else 'Detached HEAD'
        info['commit'] = commit.stdout.strip() if commit.returncode == 0 else None
        status = git('status', '--porcelain', '--untracked-files=normal')
        info['dirty'] = bool(status.stdout.strip()) if status.returncode == 0 else None
        if info['commit'] is None:
            info['notice'] = 'Repository initialized; no commits yet.'
    except FileNotFoundError:
        info['notice'] = 'Git is not available in this environment.'
    except (OSError, subprocess.TimeoutExpired):
        info['notice'] = 'Git information is currently unavailable.'
    return info


def confined(base, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('Paths must be relative to the scenario.')
    resolved = (base / relative).resolve()
    if not resolved.is_relative_to(CATALOG.resolve()):
        raise ValueError('The path escapes the approved Oracle catalog.')
    return resolved


def strict_json(text):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError('Duplicate JSON key.')
            value[key] = item
        return value
    def invalid_constant(value):
        raise ValueError('Non-finite JSON number.')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def discover():
    tests, errors, seen, duplicate_ids = {}, [], set(), set()
    for manifest in sorted(SCENARIOS.rglob('oracle.json')):
        try:
            if not manifest.resolve().is_relative_to(SCENARIOS.resolve()):
                raise ValueError('Descriptor outside the catalog.')
            item = strict_json(manifest.read_text(encoding='utf-8'))
            if not isinstance(item, dict):
                raise ValueError('The descriptor must be a JSON object.')
            for key in ('id', 'title', 'category', 'description', 'criterion', 'mode', 'form', 'prerequisites'):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    raise ValueError(f'Missing or invalid field: {key}')
            if item['id'] in seen:
                duplicate_ids.add(item['id'])
                tests.pop(item['id'], None)
                raise ValueError('Duplicate identifier; all conflicting entries are disabled.')
            seen.add(item['id'])
            if type(item.get('schema_version')) is not int or item['schema_version'] != 1:
                raise ValueError('Unsupported or missing catalog schema_version.')
            if item['mode'] not in ('script', 'manual') or item['form'] not in (
                'deterministic', 'agentic_execution', 'agentic_judgment', 'characterization', 'metamorphic'):
                raise ValueError('Unknown execution mode or Oracle form.')
            if not item['id'].startswith('ORACLE-') or (type(item.get('demo', False)) is not bool):
                raise ValueError('Invalid Oracle identifier or example marker.')
            item['manifest'] = manifest.relative_to(CATALOG).as_posix()
            item['_manifest'] = str(manifest)
            item['_descriptor_sha256'] = file_hash(manifest)
            if item['mode'] == 'script':
                if item['form'] in ('agentic_execution', 'agentic_judgment'):
                    raise ValueError('Agent-operated scenarios require manual display or a separately qualified adapter.')
                limit = item.get('timeout_seconds', 60)
                if type(limit) is not int or not 1 <= limit <= 3600:
                    raise ValueError('timeout_seconds must be an integer from 1 to 3600.')
                item['timeout_seconds'] = limit
                script = confined(manifest.parent, item['script'])
                baseline = confined(manifest.parent, item['baseline'])
                if script.suffix != '.py' or not script.is_file() or not baseline.is_file():
                    raise ValueError('Python script or baseline not found.')
                item['_script'] = str(script)
                item['_expected'] = strict_json(baseline.read_text(encoding='utf-8'))
                item['_baseline'] = str(baseline)
                item['_baseline_sha256'] = file_hash(baseline)
                item['_script_sha256'] = file_hash(script)
            else:
                steps = item.get('steps')
                if not isinstance(steps, list) or not steps or not all(
                    isinstance(s, dict) and isinstance(s.get('action'), str)
                    and isinstance(s.get('expected'), str) for s in steps):
                    raise ValueError('Invalid manual steps.')
            tests[item['id']] = item
        except (ValueError, KeyError, OSError) as exc:
            errors.append(f'{manifest.relative_to(CATALOG)} : {exc}')
    for identifier in duplicate_ids:
        tests.pop(identifier, None)
    return tests, errors


def differences(expected, actual, path='$'):
    if type(expected) is not type(actual):
        return [f'{path} : expected {json.dumps(expected, ensure_ascii=False)}, observed {json.dumps(actual, ensure_ascii=False)}']
    if isinstance(expected, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            if key not in actual:
                result.append(f'{path}.{key} : expected field missing')
            elif key not in expected:
                result.append(f'{path}.{key} : unexpected field')
            else:
                result.extend(differences(expected[key], actual[key], f'{path}.{key}'))
        return result
    if isinstance(expected, list):
        result = []
        if len(expected) != len(actual):
            result.append(f'{path} : {len(expected)} items expected, {len(actual)} observed')
        for i, (left, right) in enumerate(zip(expected, actual)):
            result.extend(differences(left, right, f'{path}[{i}]'))
        return result
    return [] if expected == actual else [f'{path} : expected {json.dumps(expected, ensure_ascii=False)}, observed {json.dumps(actual, ensure_ascii=False)}']


class Demo:
    def __init__(self, project):
        self.project_path = project
        self.project = project_info(project)
        self.tests, self.errors = discover()
        self.results = {}
        self.job = None
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.token = secrets.token_urlsafe(32)
        self.session = secrets.token_hex(6)
        self.output = project / '.scratchpad' / 'oracle-lab' / 'runs' / self.session
        if not self.output.resolve().is_relative_to((project / '.scratchpad').absolute()) or not self.output.resolve().is_relative_to(project.resolve()):
            raise ValueError('Scratch output escapes the project; use a reviewed local path.')

    def snapshot(self):
        with self.lock:
            catalog = [{k: v for k, v in item.items() if not k.startswith('_')} for item in self.tests.values()]
            return copy.deepcopy({'demo': any(t.get('demo', False) for t in self.tests.values()), 'token': self.token, 'session': self.session,
                'project': self.project, 'tests': catalog, 'catalog_errors': self.errors,
                'results': self.results, 'job': self.job})

    def persist(self):
        if not self.output.resolve().is_relative_to((self.project_path / '.scratchpad').absolute()):
            raise ValueError('Scratch output path changed.')
        self.output.mkdir(parents=True, exist_ok=True)
        report = self.snapshot()
        report.pop('token')
        report['disclaimer'] = DISCLAIMER
        report['saved_at'] = now()
        temporary = self.output / 'report.tmp'
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        temporary.replace(self.output / 'report.json')

    def start(self, ids):
        with self.lock:
            if self.job and self.job['status'] == 'running':
                raise ValueError('A run is already in progress.')
            if not isinstance(ids, list) or not ids or len(ids) != len(set(ids)):
                raise ValueError('Empty or duplicate selection.')
            if any(not isinstance(i, str) or i not in self.tests or self.tests[i]['mode'] != 'script' for i in ids):
                raise ValueError('Only registered catalog scripts can be run.')
            for identifier in ids:
                item = self.tests[identifier]
                if any(file_hash(item[key]) != item[key + '_sha256'] for key in ('_descriptor', '_script', '_baseline') if key != '_descriptor'):
                    raise ValueError('Test files changed; refresh the catalog before running.')
                if file_hash(item['_manifest']) != item['_descriptor_sha256']:
                    raise ValueError('Descriptor changed; refresh the catalog before running.')
            self.project = project_info(self.project_path)
            self.stop.clear()
            self.job = {'id': secrets.token_hex(6), 'status': 'running', 'ids': ids,
                        'finished': 0, 'total': len(ids), 'started_at': now()}
            for identifier in ids:
                self.results[identifier] = {'status': 'queued', 'source': 'script', 'logs': [], 'output': [], 'demo': self.tests[identifier].get('demo', False),
                    'descriptor_sha256': self.tests[identifier]['_descriptor_sha256'],
                    'script_sha256': self.tests[identifier]['_script_sha256'],
                    'baseline_sha256': self.tests[identifier]['_baseline_sha256']}
            threading.Thread(target=self.work, args=(list(ids),), daemon=True).start()

    def work(self, ids):
        for identifier in ids:
            if self.stop.is_set():
                with self.lock:
                    self.results[identifier].update(status='cancelled', message='Cancelled before execution.', finished_at=now())
            else:
                self.execute(identifier)
            with self.lock:
                self.job['finished'] += 1
                self.persist()
        with self.lock:
            self.job.update(status='cancelled' if self.stop.is_set() else 'complete', finished_at=now())
            self.persist()

    def execute(self, identifier):
        item = self.tests[identifier]
        command = [sys.executable, '-u', item['_script']]
        with self.lock:
            result = self.results[identifier]
            result.update(status='running', started_at=now(), message='Starting script…',
                          project=copy.deepcopy(self.project), expected=item['_expected'],
                          command=subprocess.list2cmdline(command) if os.name == 'nt' else shlex.join(command),
                          cwd=str(Path(item['_script']).parent), exit_code=None)
        started = time.monotonic()
        proc = None
        try:
            env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
            proc = subprocess.Popen(command, cwd=Path(item['_script']).parent,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace',
                env=env, creationflags=CREATION_FLAGS)
            events = queue.Queue(maxsize=128)
            def reader():
                for line in iter(lambda: proc.stdout.readline(8193), ''):
                    events.put(line[:8000])
                events.put(None)
            threading.Thread(target=reader, daemon=True).start()
            actual, received, blocked = None, False, None
            while True:
                if self.stop.is_set():
                    with self.lock:
                        result.update(status='cancelled', message='Execution stopped on request.')
                    break
                if time.monotonic() - started > item['timeout_seconds']:
                    raise TimeoutError('The script exceeded its configured time limit.')
                try:
                    line = events.get(timeout=.15)
                except queue.Empty:
                    continue
                if line is None:
                    break
                with self.lock:
                    result['output'].append(line.rstrip('\r\n'))
                    result['output'] = result['output'][-300:]
                    try:
                        event = strict_json(line)
                    except ValueError:
                        event = {'type': 'log', 'message': line.strip()}
                    if not isinstance(event, dict):
                        raise ValueError('Invalid process event.')
                    if event.get('type') == 'result':
                        if received or blocked is not None or 'actual' not in event:
                            raise ValueError('Missing or duplicate result.')
                        actual, received = event['actual'], True
                    elif event.get('type') == 'blocked':
                        if received or blocked is not None:
                            raise ValueError('Mixed or duplicate terminal events.')
                        blocked = str(event.get('message', 'Missing prerequisite.'))
                    else:
                        result['message'] = str(event.get('message', ''))[:2000]
                        result['logs'].append({'at': now(), 'message': result['message']})
                        result['logs'] = result['logs'][-100:]
            if result['status'] != 'cancelled':
                exit_code = proc.wait(timeout=2)
                with self.lock:
                    if exit_code:
                        raise RuntimeError(f'The process exited with code {exit_code}.')
                    if blocked:
                        result.update(status='blocked', message=blocked)
                    elif not received:
                        raise ValueError('The script did not return a structured result.')
                    else:
                        diff = differences(item['_expected'], actual)
                        result.update(status='fail' if diff else 'pass', actual=actual, differences=diff,
                                      message='Output differs from the baseline.' if diff else 'Output matches the baseline.')
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
            with self.lock:
                result.update(status='error', message=str(exc))
        finally:
            if proc and proc.poll() is None:
                proc.kill()
                proc.wait()
            with self.lock:
                result.update(finished_at=now(), duration=round(time.monotonic() - started, 2),
                              exit_code=proc.returncode if proc else None)

    def manual(self, body):
        with self.lock:
            item = self.tests.get(body.get('id'))
            if not item or item['mode'] != 'manual':
                raise ValueError('Unknown manual scenario.')
            status = body.get('status')
            checked = body.get('checked', [])
            notes = str(body.get('notes', '')).strip()[:4000]
            if status not in ('pass', 'fail', 'blocked', 'incomplete'):
                raise ValueError('Choose a result.')
            if not isinstance(checked, list) or any(type(i) is not int or not 0 <= i < len(item['steps']) for i in checked):
                raise ValueError('Invalid steps.')
            if status == 'pass' and len(set(checked)) != len(item['steps']):
                raise ValueError('Verify every step before marking the test as passed.')
            if status in ('fail', 'blocked') and not notes:
                raise ValueError('Briefly describe your observation.')
            self.results[item['id']] = {'status': status, 'source': 'human', 'notes': notes,
                'checked': checked, 'finished_at': now(), 'demo': item.get('demo', False),
                'descriptor_sha256': item['_descriptor_sha256'],
                'project': project_info(self.project_path), 'message': 'Result reported by the user.'}
            self.persist()


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, data, content_type='application/json; charset=utf-8'):
        payload = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(payload)

    def valid_host(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.valid_host():
            return self.respond(403, {'error': 'Host not allowed.'})
        path = urlsplit(self.path).path
        if path == '/api/state':
            return self.respond(200, self.server.demo.snapshot())
        if path == '/api/report':
            report = self.server.demo.snapshot()
            report.pop('token')
            report['disclaimer'] = DISCLAIMER
            return self.respond(200, report)
        files = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if path not in files:
            return self.respond(404, {'error': 'Not found.'})
        name, mime = files[path]
        self.respond(200, (ROOT / 'web' / name).read_bytes(), mime)

    def do_POST(self):
        origin = self.headers.get('Origin')
        if not self.valid_host() or (origin and origin != f'http://{self.headers.get("Host")}'):
            return self.respond(403, {'error': 'Origin not allowed.'})
        if not secrets.compare_digest(self.headers.get('X-Oracle-Token', ''), self.server.demo.token):
            return self.respond(403, {'error': 'Local session token required.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000 or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                raise ValueError('Invalid JSON request.')
            body = strict_json(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError('JSON object expected.')
            path, demo = urlsplit(self.path).path, self.server.demo
            if path == '/api/run':
                demo.start(body.get('ids'))
            elif path == '/api/stop':
                demo.stop.set()
            elif path == '/api/manual':
                demo.manual(body)
            elif path == '/api/refresh':
                with demo.lock:
                    if demo.job and demo.job['status'] == 'running':
                        raise ValueError('Refresh the catalog after the run completes.')
                    demo.tests, demo.errors = discover()
                    demo.results = {k: v for k, v in demo.results.items() if k in demo.tests}
                    for identifier, result in demo.results.items():
                        item = demo.tests[identifier]
                        result['catalog_changed'] = (
                            result.get('descriptor_sha256') != item['_descriptor_sha256']
                            or (item['mode'] == 'script' and (
                                result.get('script_sha256') != item['_script_sha256']
                                or result.get('baseline_sha256') != item['_baseline_sha256'])))
                    demo.project = project_info(demo.project_path)
            else:
                return self.respond(404, {'error': 'Unknown action.'})
            self.respond(200, {'ok': True})
        except (ValueError, TypeError, KeyError) as exc:
            self.respond(400, {'error': str(exc)})

    def log_message(self, fmt, *args):
        if self.command != 'GET' or self.path not in ('/api/state',):
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--project-root', type=Path, default=CATALOG.parent)
    args = parser.parse_args()
    project = args.project_root.resolve()
    if not project.is_dir():
        parser.error('The project folder does not exist.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.demo = Demo(project)
    print(f'Oracle Lab — local runner: http://127.0.0.1:{server.server_port}', flush=True)
    print(f'Project context: {project}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.demo.stop.set()
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
```

### harnesses/lab/web/index.html

<!-- oracle-lab-file: harnesses/lab/web/index.html -->
```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Oracle Lab</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="/style.css">
  <script src="/app.js" defer></script>
</head>
<body>
  <aside class="sidebar">
    <a class="brand" href="/" aria-label="Oracle Lab, home"><span class="brand-mark">a.</span>Oracle Lab</a>
    <div class="nav-caption">TESTS</div>
    <nav id="categories" aria-label="Test categories"></nav>
    <div class="connection"><span id="connection-dot" class="dot"></span><span id="connection-text">Connecting…</span></div>
  </aside>
  <main>
    <header class="project-panel" aria-label="Project information">
      <div class="project-location"><h1 id="project-name">Loading project…</h1><code id="project-path">—</code></div>
      <span id="catalog-notice" class="demo-label" hidden>Examples included · fictional tests</span>
      <div class="project-context"><span>Branch <strong id="project-branch">—</strong></span><span>Commit <strong id="project-commit">—</strong></span><details class="project-details"><summary>Project details</summary><span id="git-state">—</span><p id="git-notice" hidden></p></details></div>
    </header>
    <div id="error-banner" class="error-banner" role="alert" hidden></div>
    <section class="workspace-head"><div><h2 id="category-title">All tests</h2><p id="category-summary">Loading catalog…</p></div><div class="workspace-tools"><button class="text-button" id="refresh" type="button">↻ Refresh</button><details class="help-details"><summary>How to use</summary><div class="help-content"><p>Select scripts to run them. Open manual scenarios to follow their steps yourself.</p><p id="results-note">Refreshing this page never starts a run.</p><p id="demo-help" hidden>These examples use fictional data and do not qualify your project. The manual scenarios describe an app that is not included.</p></div></details></div></section>
    <section id="run-progress" class="run-progress" aria-label="Latest run" hidden>
      <div class="run-summary"><strong id="run-heading"></strong><time id="run-time"></time><span id="result-summary"></span><button class="text-button" id="view-run" type="button" aria-controls="test-detail">View run →</button></div>
      <details id="run-details"><summary>Run details</summary><div class="run-detail-content"><span id="run-identity"></span><span id="run-progress-text" role="status"></span><span id="run-following" hidden>Following execution</span></div></details>
    </section>
    <section class="workspace">
      <div class="catalog-panel">
        <div class="toolbar"><span id="selection-label">Select scripts</span><button class="button primary" id="run-selection" type="button" disabled>Run selected</button><button class="button danger" id="stop" type="button" hidden>Stop run</button></div>
        <div class="table-wrap"><table><thead><tr><th class="select-cell"><input id="select-all" type="checkbox" aria-label="Select all visible scripts"></th><th>TEST</th><th>LATEST RESULT</th></tr></thead><tbody id="test-list"></tbody></table></div>
        <div class="catalog-footer"><a href="/api/report" id="download-report" download="oracle-demo-report.json">Export report ↓</a></div>
      </div>
      <aside class="detail-panel" aria-label="Test detail"><div id="test-detail"><div class="empty-detail"><h3>Select a test</h3><p>Its instructions and results will appear here.</p></div></div></aside>
    </section>
  </main>
  <div class="toast" id="toast" role="status" hidden></div>
</body>
</html>
```

### harnesses/lab/web/style.css

<!-- oracle-lab-file: harnesses/lab/web/style.css -->
```css
:root{color-scheme:light;--paper:#f6f7f5;--surface:#fff;--ink:#24342d;--muted:#68796e;--line:#e0e6df;--teal:#146b58;--nav:#192e2b;--red:#ae4036;--amber:#8a6627}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.55 'Segoe UI',system-ui,sans-serif}button,input,textarea,select{font:inherit}button,a,input,select,summary{touch-action:manipulation}button,summary{cursor:pointer}button:disabled{cursor:not-allowed;opacity:.45}a{color:var(--teal);text-decoration:none}a:hover{text-decoration:underline}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible,[tabindex]:focus-visible{outline:3px solid #70ad9b;outline-offset:3px}[hidden]{display:none!important}summary{color:var(--muted);font-size:12px;width:fit-content}summary:hover{color:var(--teal)}details[open]>summary{margin-bottom:12px}p{margin:0 0 12px}h1,h2,h3,h4{line-height:1.3}code,pre{font-family:Consolas,'Courier New',monospace}
.sidebar{width:216px;position:fixed;inset:0 auto 0 0;background:var(--nav);color:#e6eeea;display:flex;flex-direction:column;padding:28px 18px}.brand{display:flex;align-items:center;gap:11px;color:#f7fbf8;font-size:20px;font-weight:600;letter-spacing:-.5px}.brand:hover{text-decoration:none}.brand-mark{background:#c9e0b6;color:#244937;width:35px;height:39px;border-radius:10px;display:grid;place-items:center;font:29px Georgia,serif;padding-bottom:5px}.nav-caption{font-size:10px;letter-spacing:1.6px;color:#94aca0;margin:44px 12px 12px}.category{display:flex;align-items:center;gap:10px;width:100%;border:0;background:transparent;color:#bdcdc3;text-align:left;padding:12px;border-radius:7px;margin:3px 0;font-size:13px}.category:hover{background:#223e36}.category.active{background:#315147;color:white}.category-symbol{display:none}.count{margin-left:auto;color:#9eb6a6;font-size:11px}.category.active .count{color:#d2e2d6}.connection{margin-top:auto;display:flex;align-items:center;gap:8px;padding:20px 10px 0;font-size:11px;color:#acc2b3}.dot{width:6px;height:6px;border-radius:50%;background:#a8c68d}.dot.offline{background:#e7a090}
main{margin-left:216px;padding:28px 36px 40px;max-width:1900px}.project-panel{display:flex;align-items:center;flex-wrap:wrap;gap:12px 24px;padding-bottom:22px;border-bottom:1px solid var(--line)}.project-location{flex:1;min-width:0}h1{font-size:18px;letter-spacing:-.3px;font-weight:600;margin:0 0 5px}.project-location code{font-size:11px;color:var(--muted);overflow-wrap:anywhere}.demo-label{font-size:11px;color:#8a795d;white-space:nowrap}.project-context{display:flex;gap:18px;flex-wrap:wrap;flex-basis:100%;color:var(--muted);font-size:11px}.project-context strong{font-weight:500;color:#435b4a;margin-left:5px}.project-details{flex:1}.project-details summary{font-size:11px}.project-details p{margin-top:6px}.workspace-head{display:flex;justify-content:space-between;align-items:center;gap:20px;margin:26px 0 20px}h2{font-size:27px;letter-spacing:-.7px;margin:0 0 5px;font-weight:600}.workspace-head p{font-size:12px;color:var(--muted);margin:0}.workspace-tools{display:flex;align-items:baseline;gap:20px}.help-details{position:relative}.help-content{position:absolute;right:0;top:30px;width:300px;max-width:calc(100vw - 36px);padding:18px;background:white;border:1px solid var(--line);border-radius:8px;box-shadow:0 8px 25px #203e2910;z-index:3;font-size:12px;color:var(--muted)}.help-content p:last-child{margin-bottom:0}.text-button{padding:0;border:0;background:transparent;font-size:12px;color:var(--teal);font-weight:500}.text-button:hover:not(:disabled){text-decoration:underline;text-underline-offset:4px}.button{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid transparent;border-radius:6px;padding:10px 15px;font-size:12px;font-weight:600;white-space:nowrap}.primary{background:var(--teal);color:white}.primary:hover:not(:disabled){background:#0e5545}.secondary{background:white;border-color:#b6c8bc;color:var(--teal)}.secondary:hover:not(:disabled){background:#f1f6ef}.danger{background:#faebe7;color:var(--red);border-color:#e9c7bf}.button:disabled{background:#edf0eb;color:#839282;border-color:transparent;opacity:1}
.run-progress{padding:0 0 18px;margin-bottom:22px;border-bottom:1px solid var(--line)}.run-summary{display:flex;align-items:baseline;gap:10px 17px;flex-wrap:wrap;font-size:12px}.run-summary strong{font-weight:600}.run-summary time{color:var(--muted);font-size:11px}.run-summary #result-summary{color:var(--muted)}.run-summary button{margin-left:auto}.run-progress details{margin-top:8px}.run-progress summary{font-size:11px}.run-detail-content{display:flex;flex-direction:column;gap:6px;font-size:11px;color:var(--muted)}.error-banner{margin:16px 0;padding:13px 16px;background:#fff1eb;border-left:3px solid var(--red);color:var(--red);font-size:12px}
.workspace{display:grid;grid-template-columns:minmax(300px,.72fr) minmax(0,1.28fr);gap:26px;align-items:start}.catalog-panel,.detail-panel{min-width:0;background:var(--surface);border:1px solid var(--line);border-radius:9px;overflow:hidden}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:16px;min-height:70px}.toolbar>span{font-size:11px;color:var(--muted)}.table-wrap{width:100%;overflow-x:auto}table{width:100%;border-collapse:collapse}th{text-align:left;font-size:9px;font-weight:500;letter-spacing:.7px;color:var(--muted);padding:10px 8px;border-bottom:1px solid var(--line)}td{padding:17px 8px;border-bottom:1px solid #edf0eb;vertical-align:middle}.select-cell{width:34px;padding-left:15px;padding-right:4px}input[type=checkbox]{width:14px;height:14px;accent-color:var(--teal);cursor:pointer}.category-group th{padding:9px 15px;background:#f4f6f1;color:#536a5a;font-size:11px;letter-spacing:0;font-weight:600}.group-count{float:right;font-size:10px;color:#8a988c;font-weight:400}[data-test-row]{cursor:pointer}[data-test-row]:hover{background:#f7faf6}[data-test-row].selected,[data-test-row].selected:hover{background:#eaf3ed}[data-test-row].selected td:first-child{box-shadow:inset 3px 0 var(--teal)}.test-name{display:block;width:100%;border:0;background:none;color:var(--ink);padding:0;font-size:13px;font-weight:500;text-align:left;line-height:1.5}.test-name:hover{color:var(--teal)}.test-subtitle,.open-steps{font-size:10px;color:var(--muted);margin-top:5px}.open-steps{display:block;color:var(--teal);font-weight:400}.manual-mark{color:#7d9484;font-size:14px}.result-cell{min-width:94px}.badge{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:500;white-space:nowrap}.badge.pass{color:#35784c}.badge.fail,.badge.error{color:var(--red)}.badge.running{color:var(--teal)}.badge.blocked{color:var(--amber)}.badge.incomplete,.badge.cancelled,.badge.queued{color:#817483}.badge.idle{color:#a0aba0;font-weight:400}.result-origin{font-size:10px;margin-top:5px;color:var(--muted)}.result-origin.earlier{color:#8a795b}.result-date{display:none}.catalog-footer{display:flex;justify-content:flex-end;padding:13px 16px;font-size:11px}
.detail-header{padding:25px 26px 0}.detail-context{font-size:11px;color:var(--muted)}.detail-context span{margin:0 6px;color:#abb5aa}.detail-header h3{font-size:24px;font-weight:600;letter-spacing:-.5px;margin:12px 0}.detail-header>p{font-size:13px;color:var(--muted);line-height:1.8;margin-bottom:0}.detail-body{padding:20px 26px 25px}.criterion{font-size:12px;line-height:1.8;color:#617760;margin-bottom:20px}.criterion strong{display:block;font-size:11px;font-weight:600;color:#435d4a;margin-bottom:3px}.detail-actions{display:flex;align-items:center;flex-wrap:wrap;gap:18px;margin-bottom:20px}.result-context-notice{font-size:11px;color:var(--muted);line-height:1.8;margin:0 0 12px}.result-context-notice.earlier{color:#8a795b}.result-context-notice strong{font-weight:500}.result-context-notice>span{margin-left:8px}.result-context-notice p{margin:0}.empty-detail{min-height:300px;display:flex;flex-direction:column;justify-content:center;text-align:center;padding:30px}.empty-detail h3{font-size:20px;font-weight:500;margin:0 0 9px;color:#576f5b}.empty-detail p{font-size:13px;color:var(--muted);margin:0}.waiting-result{font-size:12px;color:var(--muted);margin:10px 0 20px}
.terminal{background:#142421;color:#d7e4db;border-radius:7px;overflow:hidden;margin-bottom:24px}.terminal-bar{padding:11px 15px;background:#1e322d;display:flex;align-items:center;justify-content:space-between;gap:10px}.terminal-title{font-size:12px;font-weight:500;color:#e7f0e8}.terminal-title>span{margin-right:8px;color:#b8d8a9}.terminal-indicator{font:9px Consolas,monospace;letter-spacing:.7px;color:#9daea1}.terminal-indicator.live{color:#bdddab}.terminal-scroll{height:295px;overflow:auto;padding:16px;scrollbar-color:#4b6859 #142421;font:12px/1.9 Consolas,monospace}.terminal-cwd{font-size:10px;color:#91aa9b;margin-bottom:12px;overflow-wrap:anywhere}.terminal-command{color:#c7dfb6;overflow-wrap:anywhere;margin-bottom:16px}.terminal-lines{font:inherit;margin:0;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}.terminal-cursor{color:#aed597}.terminal-footer{border-top:1px solid #2c433b;padding:9px 15px;color:#a5bdad;font:10px/1.7 Consolas,monospace}
.result-section{padding:20px 0 0;border-top:1px solid var(--line);margin-bottom:18px}.conclusion h4{font-size:20px;font-weight:600;margin:0 0 8px}.conclusion.pass h4{color:#35784c}.conclusion.fail h4,.conclusion.error h4{color:var(--red)}.conclusion.blocked h4{color:var(--amber)}.conclusion p{font-size:13px;color:var(--muted);line-height:1.8;margin:0}.differences{margin-top:14px}.differences pre{font-size:12px;color:#9c4d40;white-space:pre-wrap;overflow-wrap:anywhere;margin:0}.comparison-details{margin-top:18px}.comparison-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:15px}.compare-label{font-size:11px;color:var(--muted);margin:8px 0}.output{white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word;font-size:12px;line-height:1.8;color:#576e5b;background:#f6f8f3;padding:13px;border-radius:5px;margin:0;max-height:320px;overflow:auto}.technical-details{border-top:1px solid var(--line);padding-top:14px;margin-top:20px}.detail-meta,.result-provenance{font-size:11px;line-height:1.8;color:var(--muted);overflow-wrap:anywhere}.detail-meta p{margin:7px 0}.detail-meta code{font-size:10px}.manual-intro{font-size:12px;color:var(--muted);margin:0 0 16px}.prerequisites{margin-bottom:20px}.prerequisites p{font-size:12px;color:var(--muted)}.steps{display:grid;gap:18px;padding:0;margin:20px 0 26px;list-style:none}.step-head{display:flex;align-items:flex-start;gap:9px;font-size:13px;line-height:1.7}.step-head input{flex-shrink:0;margin-top:4px}.expected-step{font-size:12px;line-height:1.7;color:var(--muted);padding-left:27px;margin-top:4px}.field-label{display:block;font-size:12px;color:#4c6753;margin:17px 0 7px}.field-label span{font-weight:400;color:var(--muted);font-size:11px}textarea,select{width:100%;border:1px solid #cdd9cb;border-radius:5px;background:white;padding:10px 12px;font-size:13px;color:var(--ink)}textarea{resize:vertical;min-height:84px}.manual-form .button{margin-top:18px}.toast{position:fixed;right:24px;bottom:22px;background:var(--nav);color:white;padding:12px 18px;border-radius:7px;font-size:12px;z-index:5;box-shadow:0 6px 24px #163a241c}
@media(min-width:1600px){main{padding:34px 46px 40px}.workspace{grid-template-columns:minmax(350px,.65fr) minmax(0,1.35fr);gap:30px}.detail-header,.detail-body{padding-left:32px;padding-right:32px}.terminal-scroll{height:340px}}
@media(max-width:1200px){.sidebar{width:190px;padding:24px 13px}main{margin-left:190px;padding:24px}.workspace{grid-template-columns:minmax(285px,.8fr) minmax(0,1.2fr);gap:18px}.detail-header,.detail-body{padding-left:20px;padding-right:20px}.toolbar{padding:13px}.toolbar>span{font-size:10px}.button{padding:9px 12px}.detail-header h3{font-size:22px}}
@media(max-width:980px){.workspace{grid-template-columns:1fr}.detail-panel{margin-top:0}.project-context{gap:10px 17px}.project-details{flex-basis:100%}}
@media(max-width:720px){.sidebar{position:static;width:100%;padding:17px 16px 8px}.brand{font-size:18px}.brand-mark{width:30px;height:32px;font-size:24px}.nav-caption,.connection{display:none}#categories{display:flex;gap:5px;overflow:auto;margin-top:15px}.category{width:auto;flex-shrink:0;padding:8px;font-size:11px;gap:7px}.count{font-size:10px}main{margin-left:0;padding:20px 16px 30px}.project-panel{gap:10px}.project-location{flex-basis:100%}.demo-label{order:-1;font-size:10px}.project-location h1{font-size:17px}.project-location code{font-size:10px}.project-context{font-size:10px}.project-details summary{font-size:10px}.workspace-head{margin:22px 0 18px;align-items:flex-start}.workspace-tools{gap:10px;flex-direction:column;align-items:flex-end;padding-top:4px}.workspace-head h2{font-size:24px}.workspace-head p{font-size:11px}.run-summary{gap:8px 12px}.run-summary #result-summary{flex-basis:100%;font-size:11px}.run-summary button{margin-left:0}.workspace{gap:18px}.toolbar>span{font-size:11px}th{font-size:8px;letter-spacing:.3px;padding:10px 6px}td{padding:15px 6px}.select-cell{width:28px;padding-left:10px}.test-name{font-size:12px}.result-cell{min-width:86px}.badge{font-size:11px}.result-origin{font-size:9px}.detail-header,.detail-body{padding-left:18px;padding-right:18px}.detail-header h3{font-size:22px}.comparison-grid{grid-template-columns:1fr;gap:10px}.terminal-scroll{height:260px;font-size:11px}.result-context-notice>span{display:block;margin-left:0}.toast{left:16px;right:16px;bottom:16px}}
```

### harnesses/lab/web/app.js

<!-- oracle-lab-file: harnesses/lab/web/app.js -->
```javascript
'use strict';
const $ = id => document.getElementById(id);
const escapeText = text => String(text ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {idle:'Not run',queued:'Queued',running:'Running',pass:'Passed',fail:'Failed',blocked:'Blocked',error:'Error',cancelled:'Cancelled',incomplete:'Incomplete'};
const symbols = {idle:'·',queued:'·',running:'◌',pass:'✔',fail:'×',blocked:'!',error:'!',cancelled:'—',incomplete:'◐'};
let state = null, category = 'all', focused = null, selected = new Set(), loading = false, detailKey = '', tableKey = '', revealedJob = '', followRun = false, awaitingRunAfter = null;
const drafts = new Map(), terminalViews = new Set(), terminalHidden = new Set(), expandedPanels = new Map();
const badge = status => '<span class="badge '+escapeText(status)+'">'+(symbols[status] || '·')+' '+(labels[status] || escapeText(status))+'</span>';
const resultFor = id => state.results[id] || {status:'idle',logs:[],output:[]};
const isRunning = () => state?.job?.status === 'running';
const visibleTests = () => state.tests.filter(t => category === 'all' || t.category === category);
const activeTest = () => state.job?.ids.find(id => resultFor(id).status === 'running') || state.job?.ids.find(id => resultFor(id).status === 'queued');
const lastRunTest = () => [...(state.job?.ids || [])].reverse().find(id => resultFor(id).started_at);
const dateLabel = (value, compact = false) => value ? new Date(value).toLocaleString('en-GB', compact
  ? {day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}
  : {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',timeZoneName:'short'}) : 'Time unavailable';
function resultContext(id) {
  const r = resultFor(id);
  if (r.status === 'idle') return null;
  if (r.catalog_changed) return {kind:'earlier', label:'Earlier definition', when:r.finished_at || r.started_at, runId:null};
  const latest = r.source === 'script' && state.job?.ids.includes(id);
  return {
    kind: r.source === 'human' ? 'manual' : latest ? 'latest' : 'earlier',
    label: r.source === 'human' ? 'Manual feedback' : latest ? (isRunning() ? 'Current run' : 'Last run') : 'Earlier run',
    when: r.finished_at || r.started_at || (latest ? state.job.started_at : null),
    runId: latest ? state.job.id : null
  };
}
function resultStamp(id) {
  const context = resultContext(id);
  return context ? '<div class="result-origin '+context.kind+'" title="'+escapeText(dateLabel(context.when))+'">'+context.label+'</div><time class="result-date" datetime="'+escapeText(context.when)+'">'+escapeText(dateLabel(context.when,true))+'</time>' : '';
}
function focusRunTest() {
  const id = isRunning() ? activeTest() : lastRunTest();
  if (!id || !state.tests.some(t => t.id === id)) return;
  if (!visibleTests().some(t => t.id === id)) category = 'all';
  focused = id;
}
function revealDetail() {
  requestAnimationFrame(() => {
    const target = document.querySelector('#test-detail .terminal') || document.querySelector('#test-detail .detail-header');
    if (!target) return;
    const rect = target.getBoundingClientRect();
    if (rect.top < 0 || rect.bottom > innerHeight) target.scrollIntoView({block:'start',inline:'nearest'});
  });
}
function openTest(id, reveal = true) { followRun = false; focused = id; render(); if (reveal) revealDetail(); }
async function startRun(ids) {
  awaitingRunAfter = state.job?.id || '';
  followRun = true;
  if (!await action('/api/run', {ids})) followRun = false;
}
function notify(text) { $('toast').textContent = text; $('toast').hidden = false; clearTimeout(notify.timer); notify.timer = setTimeout(() => $('toast').hidden = true, 3500); }
function error(text) { $('error-banner').textContent = text || ''; $('error-banner').hidden = !text; }
async function action(path, data = {}) {
  try {
    const response = await fetch(path, {method:'POST',headers:{'Content-Type':'application/json','X-Oracle-Token':state.token},body:JSON.stringify(data)});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Action could not be completed.');
    error(''); await load(); return true;
  } catch (exception) { error(exception.message); return false; }
}
async function load() {
  if (loading) return;
  loading = true;
  try {
    const response = await fetch('/api/state', {cache:'no-store'});
    if (!response.ok) throw new Error('Server unavailable.');
    const previous = state;
    state = await response.json();
    if (previous && previous.session !== state.session) { drafts.clear(); terminalViews.clear(); terminalHidden.clear(); expandedPanels.clear(); focused = null; followRun = false; }
    if (state.job && previous?.job?.id !== state.job.id) state.job.ids.forEach(id => { terminalViews.delete(id); terminalHidden.delete(id); });
    for (const [id, result] of Object.entries(previous?.results || {})) {
      if (['running','queued'].includes(result.status) && !['running','queued'].includes(resultFor(id).status)) { terminalViews.delete(id); terminalHidden.delete(id); }
    }
    selected = new Set([...selected].filter(id => state.tests.some(t => t.id === id && t.mode === 'script')));
    if (category !== 'all' && !state.tests.some(t => t.category === category)) category = 'all';
    if (focused && !visibleTests().some(t => t.id === focused)) focused = null;
    // A user's navigation always wins over automatic execution following.
    if (followRun && (awaitingRunAfter === null || (state.job?.id || '') !== awaitingRunAfter)) {
      awaitingRunAfter = null;
      focusRunTest();
      if (!isRunning()) followRun = false;
    }
    if ($('connection-dot').classList.contains('offline')) error('');
    $('connection-dot').classList.remove('offline'); $('connection-text').textContent = 'Runner connected';
    render();
  } catch (exception) {
    $('connection-dot').classList.add('offline'); $('connection-text').textContent = 'Runner disconnected';
    error('Connection lost. Check that the local server is running.');
    $('run-selection').disabled = true;
  } finally { loading = false; }
}
function render() {
  const p = state.project;
  $('catalog-notice').hidden = !state.demo; $('demo-help').hidden = !state.demo;
  $('project-name').textContent = p.name; $('project-path').textContent = p.path;
  $('project-branch').textContent = p.git ? p.branch : 'No valid repository';
  $('project-commit').textContent = p.commit ? p.commit.slice(0, 9) : 'No commit';
  $('project-commit').title = p.commit || 'No commit available';
  $('git-state').textContent = !p.git ? 'Git state unavailable' : p.dirty === null ? 'Local state unavailable' : p.dirty ? 'Local changes' : 'Clean repository';
  $('git-notice').textContent = p.notice; $('git-notice').hidden = !p.notice;
  const categories = [...new Set(state.tests.map(t => t.category))].sort((a,b) => a.localeCompare(b,'en'));
  const nav = [{name:'all',label:'All tests',count:state.tests.length},...categories.map(c => ({name:c,label:c,count:state.tests.filter(t => t.category === c).length}))];
  const navKey = JSON.stringify([nav,category]);
  if ($('categories').dataset.key !== navKey) {
    $('categories').innerHTML = nav.map((c,i) => '<button type="button" class="category '+(c.name === category ? 'active' : '')+'" data-category="'+escapeText(c.name)+'" aria-pressed="'+(c.name === category)+'"><span class="category-symbol" aria-hidden="true">'+['◫','◈','▤','↗'][i%4]+'</span>'+escapeText(c.label)+'<span class="count">'+c.count+'</span></button>').join('');
    $('categories').dataset.key = navKey;
  }
  const tests = visibleTests(), scripts = tests.filter(t => t.mode === 'script'), manualCount = tests.length-scripts.length;
  $('category-title').textContent = category === 'all' ? 'All tests' : category;
  $('category-summary').textContent = tests.length+' tests · '+scripts.length+' scripts · '+manualCount+' manual';
  // Do not rebuild the list for every line received from the process.
  const key = JSON.stringify([tests,focused,[...selected],tests.map(t => [resultFor(t.id).status,resultContext(t.id)]),isRunning()]);
  if (key !== tableKey) {
    const active = document.activeElement, focusAttribute = active?.hasAttribute('data-open') ? 'data-open' : active?.hasAttribute('data-select') ? 'data-select' : null;
    const focusId = focusAttribute ? active.getAttribute(focusAttribute) : null;
    const row = t => '<tr data-test-row="'+escapeText(t.id)+'" class="'+(focused === t.id ? 'selected' : '')+'"><td class="select-cell">'+(t.mode === 'script' ? '<input type="checkbox" data-select="'+escapeText(t.id)+'" aria-label="Select '+escapeText(t.title)+'" '+(selected.has(t.id)?'checked':'')+' '+(isRunning()?'disabled':'')+'>' : '<span class="manual-mark" aria-hidden="true">↗</span>')+'</td><td><button class="test-name" data-open="'+escapeText(t.id)+'" type="button" aria-pressed="'+(focused === t.id)+'" aria-controls="test-detail">'+escapeText(t.title)+(t.mode==='manual'?'<span class="open-steps">Manual · Open steps →</span>':'')+'</button>'+(t.mode==='script'?'<div class="test-subtitle">Script</div>':'')+'</td><td class="result-cell">'+badge(resultFor(t.id).status)+resultStamp(t.id)+'</td></tr>';
    $('test-list').innerHTML = category === 'all'
      ? categories.map(c => { const group = tests.filter(t => t.category === c); return '<tr class="category-group"><th colspan="3"><span>'+escapeText(c)+'</span><span class="group-count">'+group.length+' tests</span></th></tr>'+group.map(row).join(''); }).join('')
      : tests.map(row).join('');
    if (focusAttribute) [...$('test-list').querySelectorAll('['+focusAttribute+']')].find(el => el.getAttribute(focusAttribute) === focusId)?.focus({preventScroll:true});
    tableKey = key;
  }
  $('select-all').disabled = !scripts.length || isRunning();
  $('select-all').checked = !!scripts.length && scripts.every(t => selected.has(t.id));
  $('select-all').indeterminate = scripts.some(t => selected.has(t.id)) && !$('select-all').checked;
  $('selection-label').textContent = selected.size ? selected.size+' selected' : 'Select scripts';
  $('run-selection').disabled = !selected.size || isRunning(); $('run-selection').hidden = isRunning();
  $('stop').hidden = !isRunning(); $('refresh').disabled = isRunning();
  const job = state.job; $('run-progress').hidden = !job;
  if (job) {
    const id = isRunning() ? activeTest() : lastRunTest(), test = state.tests.find(t => t.id === id);
    $('run-heading').textContent = isRunning() ? 'Run in progress' : 'Last run';
    $('run-time').textContent = dateLabel(job.started_at,true);
    $('run-time').dateTime = job.started_at;
    $('run-time').title = dateLabel(job.started_at);
    $('run-identity').textContent = '#'+job.id+' · Started '+dateLabel(job.started_at);
    $('run-progress').classList.toggle('saved', !isRunning());
    $('run-progress-text').textContent = (isRunning() ? 'Running' : job.status === 'cancelled' ? 'Run cancelled' : 'Run complete')+' · '+job.finished+'/'+job.total+' processed'+(isRunning() && test ? ' · '+test.title : '');
    $('view-run').textContent = isRunning() ? 'View live test →' : 'View last result →';
    $('view-run').hidden = !test;
    $('run-following').hidden = !isRunning() || !followRun;
  }
  const results = Object.values(state.results);
  const runResults = (job?.ids || []).map(resultFor).filter(r=>!r.catalog_changed), count = status => runResults.filter(r => r.status === status).length;
  $('result-summary').textContent = job
    ? [['pass','passed'],['fail','failed'],['blocked','blocked'],['error','errors'],['cancelled','cancelled']].filter(([status])=>count(status)).map(([status,label])=>count(status)+' '+label).join(' · ') || job.finished+'/'+job.total+' complete'
    : results.length ? 'Saved manual feedback · no scripted run yet.' : 'No tests run in this server session.';
  $('results-note').textContent = results.length
    ? 'Showing the latest result per test, not a full history. Refreshing does not rerun tests. Use Run selected to start a new run.'
    : 'Select scripts to start a new run, or open a manual scenario. Refreshing this page never starts a run.';
  if (state.catalog_errors.length) error('Catalog: '+state.catalog_errors.join(' · '));
  renderDetail();
}
function terminalMarkup(r, live) {
  const transcript = r.output?.join('\n') || (live ? 'Waiting for process output…' : 'No process output was captured.');
  return '<section class="terminal" aria-label="Process terminal"><div class="terminal-bar"><span class="terminal-title"><span aria-hidden="true">›_</span> Process terminal</span><span class="terminal-indicator '+(live?'live':'')+'">'+(live?'● LIVE':'SAVED OUTPUT')+'</span></div><div class="terminal-scroll" id="terminal-output" tabindex="0" role="log" aria-label="Live process output" aria-live="off"><div class="terminal-cwd">cwd: '+escapeText(r.cwd || 'Preparing working directory…')+'</div><div class="terminal-command"><span>$ </span>'+escapeText(r.command || 'Preparing command…')+'</div><pre class="terminal-lines">'+escapeText(transcript)+'</pre>'+(live?'<span class="terminal-cursor" aria-hidden="true">▌</span>':'')+'</div><div class="terminal-footer">'+(live ? 'Streaming stdout + stderr · read-only' : 'Process exit: '+(r.exit_code ?? 'not available')+' · Oracle verdict: '+escapeText(labels[r.status] || r.status))+'</div></section>';
}
function conclusions(r) {
  const title = {pass:'Passed — output matches',fail:'Failed — output differs',blocked:'Blocked — prerequisite missing',error:'The test could not complete',cancelled:'Run cancelled',incomplete:'Incomplete'}[r.status] || 'Test result';
  const explanation = {pass:'All compared values matched the baseline.',fail:'The script completed, but its output did not match the expected result.',cancelled:'This run does not establish whether the expected behavior is satisfied.'}[r.status] || r.message;
  return '<section class="conclusion '+escapeText(r.status)+'"><h4>'+title+'</h4>'+(explanation?'<p>'+escapeText(explanation)+'</p>':'')+'</section>';
}
function renderDetail(force = false) {
  // Preserve disclosures independently of polling and terminal visibility.
  const previousTest = $('test-detail').dataset.test;
  if (previousTest) expandedPanels.set(previousTest,new Set([...$('test-detail').querySelectorAll('details[data-disclosure][open]')].map(el=>el.dataset.disclosure)));
  const t = visibleTests().find(t => t.id === focused);
  if (!t) {
    if (detailKey !== 'empty' || force) {
      $('test-detail').innerHTML = '<div class="empty-detail"><h3>Select a test</h3><p>Its instructions and results will appear here.</p></div>';
      delete $('test-detail').dataset.test; detailKey = 'empty';
    }
    return;
  }
  const r = resultFor(t.id), live = ['running','queued'].includes(r.status);
  const hasResult = !['idle','running','queued'].includes(r.status);
  const showTerminal = terminalViews.has(t.id) || (live && !terminalHidden.has(t.id));
  const context = resultContext(t.id);
  const nextKey = JSON.stringify([t,r,context,t.mode === 'script' && isRunning(),showTerminal,!!selected.size]);
  if (nextKey === detailKey && !force) return;
  const activeId = $('test-detail').contains(document.activeElement) ? document.activeElement.id : null;
  const oldTerminal = $('terminal-output'), oldTop = oldTerminal?.scrollTop || 0;
  const sameTest = previousTest === t.id;
  const followBottom = !oldTerminal || !sameTest || oldTerminal.scrollHeight-oldTerminal.scrollTop-oldTerminal.clientHeight < 32;
  const disclosure = (name, title, body, className='') => '<details class="'+className+'" data-disclosure="'+name+'" '+(expandedPanels.get(t.id)?.has(name)?'open':'')+'><summary>'+title+'</summary>'+body+'</details>';
  detailKey = nextKey; $('test-detail').dataset.test = t.id;
  const base = '<div class="detail-header"><div class="detail-context">'+escapeText(t.category)+' <span>/</span> '+(t.mode==='script'?'Scripted test':'Manual walkthrough')+'</div><h3>'+escapeText(t.title)+'</h3><p>'+escapeText(t.description)+'</p></div><div class="detail-body"><div class="criterion"><strong>Expected behavior</strong>'+escapeText(t.criterion)+'</div>';
  const resultNotice = context ? '<div class="result-context-notice '+context.kind+'" title="'+escapeText(dateLabel(context.when))+'"><strong>'+context.label+'</strong><span>'+escapeText(dateLabel(context.when,true))+'</span>'+(context.kind==='earlier'?(r.catalog_changed?'<p>Result from an earlier test definition. Run again before using it.</p>':'<p>Not rerun in the latest run.</p>'):'')+'</div>' : '';
  const provenance = r.finished_at ? '<div class="result-provenance">'+(r.source==='human'?'User-reported result':'Automatic comparison')+' · '+escapeText(dateLabel(r.finished_at))+(r.duration ? ' · '+r.duration+' s' : '')+'</div>' : '';
  if (t.mode === 'script') {
    const canShowTerminal = live || r.started_at || r.output?.length;
    const controls = '<div class="detail-actions"><button class="button '+(selected.size?'secondary':'primary')+'" id="run-one" type="button" '+(isRunning()?'disabled':'')+'>'+(live?'Running…':r.status==='idle'?'Run test':'Run again')+'</button>'+(canShowTerminal ? '<button class="text-button" id="toggle-terminal" type="button" aria-expanded="'+showTerminal+'" aria-controls="execution-terminal">'+(showTerminal?'Hide terminal':'Show terminal')+'</button>':'')+'</div>';
    const comparison = 'actual' in r ? disclosure('comparison','Compare expected and actual','<div class="comparison-grid"><div><p class="compare-label">Expected</p><pre class="output">'+escapeText(JSON.stringify(r.expected,null,2))+'</pre></div><div><p class="compare-label">Observed</p><pre class="output">'+escapeText(JSON.stringify(r.actual,null,2))+'</pre></div></div>','comparison-details') : '';
    const results = hasResult ? '<section id="execution-results" class="result-section" aria-label="Test results">'+resultNotice+conclusions(r)+(r.differences?.length ? '<div class="differences"><pre>'+escapeText(r.differences.join('\n'))+'</pre></div>':'')+comparison+'</section>' : '<p class="waiting-result">'+(live?'Waiting for this run’s result…':'This test has not been run yet.')+'</p>';
    const technical = disclosure('technical','Technical details','<div class="detail-meta">'+provenance+(context?.runId?'<p>Run: <code>'+escapeText(context.runId)+'</code></p>':'')+'<p>Baseline: <code>'+escapeText(t.baseline)+'</code></p><p>Descriptor: <code>'+escapeText(t.manifest)+'</code></p>'+('exit_code' in r?'<p>Process exit code: '+escapeText(r.exit_code ?? 'Unavailable')+'</p>':'')+'</div>','technical-details');
    // The terminal and the results are siblings, never alternative views.
    $('test-detail').innerHTML = base+controls+'<div id="execution-terminal" '+(showTerminal?'':'hidden')+'>'+(showTerminal?terminalMarkup(r,live):'')+'</div>'+results+technical+'</div>';
    if (showTerminal) {
      const box = $('terminal-output'); box.scrollTop = followBottom ? box.scrollHeight : oldTop;
      const runKey = state.session+':'+state.job?.id;
      if (live && revealedJob !== runKey) {
        revealedJob = runKey;
        requestAnimationFrame(() => document.querySelector('.terminal')?.scrollIntoView({block:'nearest',inline:'nearest'}));
      }
    }
  } else {
    if (!drafts.has(t.id)) drafts.set(t.id,{checked:r.checked || [],notes:r.notes || '',status:r.source==='human'?r.status:''});
    const d = drafts.get(t.id);
    const prerequisites = disclosure('prerequisites','Prerequisites','<p>'+escapeText(t.prerequisites)+'</p>','prerequisites');
    $('test-detail').innerHTML = base+(r.source==='human'?'<div class="manual-saved">'+badge(r.status)+resultNotice+'</div>':'')+'<p class="manual-intro">'+(t.demo?'Demo walkthrough — the fictional app is not included.':'Follow the steps, then record your result.')+'</p>'+prerequisites+'<form class="manual-form" id="manual-form"><ol class="steps">'+t.steps.map((s,i)=>'<li><label class="step-head"><input type="checkbox" data-step="'+i+'" '+(d.checked.includes(i)?'checked':'')+'><span>'+(i+1)+'. '+escapeText(s.action)+'</span></label><div class="expected-step">Expected: '+escapeText(s.expected)+'</div></li>').join('')+'</ol><label class="field-label" for="manual-status">Your result</label><select id="manual-status" required><option value="">Choose a result…</option>'+[['pass','Passed — every step verified'],['fail','Failed'],['blocked','Unable to run'],['incomplete','Incomplete']].map(([v,label])=>'<option value="'+v+'" '+(d.status===v?'selected':'')+'>'+label+'</option>').join('')+'</select><label class="field-label" for="manual-notes">Your observation <span>(required for failures or blockers)</span></label><textarea id="manual-notes" maxlength="4000" placeholder="What did you observe?">'+escapeText(d.notes)+'</textarea><button class="button '+(selected.size?'secondary':'primary')+'" type="submit">Save feedback</button></form>'+provenance+'</div>';
  }
  if (activeId) $(activeId)?.focus({preventScroll:true});
}
$('categories').addEventListener('click', event => { const button = event.target.closest('[data-category]'); if (!button) return; followRun = false; category = button.dataset.category; focused = null; render(); });
$('test-list').addEventListener('click', event => { if (event.target.closest('input')) return; const row = event.target.closest('[data-test-row]'); if (row) openTest(row.dataset.testRow); });
$('test-list').addEventListener('change', event => { if (!event.target.matches('[data-select]')) return; const id = event.target.dataset.select; event.target.checked ? selected.add(id) : selected.delete(id); openTest(id, false); });
$('select-all').addEventListener('change', event => { visibleTests().filter(t=>t.mode==='script').forEach(t => event.target.checked ? selected.add(t.id) : selected.delete(t.id)); render(); });
$('run-selection').addEventListener('click', () => startRun([...selected]));
$('view-run').addEventListener('click', () => { awaitingRunAfter = null; followRun = isRunning(); focusRunTest(); render(); revealDetail(); });
$('stop').addEventListener('click', () => action('/api/stop'));
$('refresh').addEventListener('click', async () => { if (await action('/api/refresh')) notify('Catalog and project information refreshed.'); });
$('test-detail').addEventListener('click', event => {
  if (event.target.closest('#run-one')) startRun([focused]);
  if (event.target.closest('#toggle-terminal')) {
    if ($('execution-terminal') && !$('execution-terminal').hidden) { terminalViews.delete(focused); terminalHidden.add(focused); }
    else { terminalViews.add(focused); terminalHidden.delete(focused); }
    renderDetail(true);
  }
});
$('test-detail').addEventListener('input', () => { if (!$('manual-form')) return; drafts.set(focused,{checked:[...document.querySelectorAll('[data-step]:checked')].map(e=>Number(e.dataset.step)),notes:$('manual-notes').value,status:$('manual-status').value}); });
$('test-detail').addEventListener('submit', async event => { if (event.target.id!=='manual-form') return; event.preventDefault(); const saved = focused; if (await action('/api/manual',{id:saved,...drafts.get(saved)})) notify('Your feedback was saved.'); });
$('download-report').addEventListener('click', async event => { event.preventDefault(); try {const response=await fetch('/api/report'); if(!response.ok)throw new Error('Report unavailable.'); const blob=new Blob([JSON.stringify(await response.json(),null,2)],{type:'application/json'}); const url=URL.createObjectURL(blob); const link=document.createElement('a');link.href=url;link.download='oracle-lab-report.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}catch(e){error(e.message);} });
load(); setInterval(load, 350);
```

### scenarios/examples/csv/oracle.json

<!-- oracle-lab-file: scenarios/examples/csv/oracle.json -->
```json
{
  "schema_version": 1,
  "id": "ORACLE-example-csv-rows-a19d40",
  "title": "Example: preserve CSV rows",
  "category": "Examples",
  "description": "Fictional, in-memory CSV fixture; no product is exercised.",
  "criterion": "The three sample rows and two columns survive a CSV round trip.",
  "form": "deterministic",
  "mode": "script",
  "prerequisites": "Python 3.10+; no service or credentials required.",
  "script": "run.py",
  "baseline": "expected.json",
  "timeout_seconds": 10,
  "demo": true
}
```

### scenarios/examples/csv/run.py

<!-- oracle-lab-file: scenarios/examples/csv/run.py -->
```python
"""Fictional fixture round trip; not product evidence."""
import csv
import io
import json

print(json.dumps({"type": "log", "message": "Round-tripping three fictional CSV rows."}), flush=True)
rows = [["1", "Alpha"], ["2", "Beta"], ["3", "Gamma"]]
stream = io.StringIO()
writer = csv.writer(stream)
writer.writerow(["id", "name"])
writer.writerows(rows)
observed = list(csv.reader(io.StringIO(stream.getvalue())))
print(json.dumps({"type": "result", "actual": {"columns": observed[0], "rows": observed[1:]}}), flush=True)
```

### scenarios/examples/csv/expected.json

<!-- oracle-lab-file: scenarios/examples/csv/expected.json -->
```json
{
  "columns": [
    "id",
    "name"
  ],
  "rows": [
    [
      "1",
      "Alpha"
    ],
    [
      "2",
      "Beta"
    ],
    [
      "3",
      "Gamma"
    ]
  ]
}
```

### scenarios/examples/signout/oracle.json

<!-- oracle-lab-file: scenarios/examples/signout/oracle.json -->
```json
{
  "schema_version": 1,
  "id": "ORACLE-example-signout-b70e32",
  "title": "Example: sign out securely",
  "category": "Examples",
  "description": "A guided scenario for a fictional app, not provided by this starter.",
  "criterion": "Private content is inaccessible after signing out.",
  "form": "agentic_execution",
  "mode": "manual",
  "prerequisites": "Illustration only. For a real test, use an authorized local app and disposable account.",
  "steps": [
    {
      "action": "Open the account menu and sign out.",
      "expected": "The sign-in page appears."
    },
    {
      "action": "Go Back, then open a known private URL.",
      "expected": "No private content is exposed; signing in is required."
    }
  ],
  "demo": true
}
```

