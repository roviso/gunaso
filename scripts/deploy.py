#!/usr/bin/env python3
"""Deploy Gunaso on this server (bare-metal: gunicorn via systemd, nginx in front).

What it does, in order:

  1. Preflight   — tools present, git state, `manage.py check`, no missing
                   migrations (`makemigrations --check`), `nginx -t`.
  2. Dependencies — `pip install -r requirements.txt`, `yarn install --frozen-lockfile`.
  3. Frontend    — `yarn build`, then swap the build into backend/gunaso-api/frontend
                   (previous build kept in .deploy/frontend.prev for rollback)
                   and `collectstatic`.
  4. Database    — show the migration plan; if anything is pending, take a
                   pg_dump backup into .deploy/backups/ and `migrate`.
  5. Restart     — `systemctl restart gunaso.service`, wait until active.
  6. Verify      — health endpoint and SPA over the gunicorn socket, built
                   assets present in STATIC_ROOT, then the public URL.

Migrate happens *after* everything slow (build, collectstatic) and right
before the restart: old code keeps serving until the last moment, and the
window where old code runs against the new schema is only the restart.

Usage (run as root from anywhere):

    python3 scripts/deploy.py                 # full deploy of the checked-out commit
    python3 scripts/deploy.py --pull          # git pull --ff-only first
    python3 scripts/deploy.py --dry-run       # read-only checks + show what would run
    python3 scripts/deploy.py --skip-frontend # backend-only change
    python3 scripts/deploy.py --rollback-frontend   # restore the previous SPA build

Only the Python standard library is used, so it runs with the system python3.
"""
from __future__ import annotations

import argparse
import datetime as dt
import http.client
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

# ── Layout ────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parent.parent
BACKEND = REPO / 'backend' / 'gunaso-api'
FRONTEND_SRC = REPO / 'frontend' / 'gunaso-ui'
FRONTEND_DIST = FRONTEND_SRC / 'dist'
FRONTEND_LIVE = BACKEND / 'frontend'          # STATICFILES_DIRS + index.html template dir
STATIC_ROOT = BACKEND / 'static'              # served by nginx at /static/
VENV_PY = BACKEND / '.venv' / 'bin' / 'python'
ENV_FILE = BACKEND / '.env'
STATE_DIR = REPO / '.deploy'                  # gitignored
BACKUP_DIR = STATE_DIR / 'backups'
FRONTEND_PREV = STATE_DIR / 'frontend.prev'
HISTORY = STATE_DIR / 'history.log'

DEFAULT_SERVICE = 'gunaso.service'
DEFAULT_SOCKET = BACKEND / 'gunaso.sock'
KEEP_BACKUPS = 10

# ── Output helpers ────────────────────────────────────────────────────────────
USE_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f'\033[{code}m{text}\033[0m' if USE_COLOR else text


def step(title: str) -> None:
    print('\n' + _c('1;36', f'▶ {title}'))


def ok(msg: str) -> None:
    print(_c('32', '  ✓ ') + msg)


def warn(msg: str) -> None:
    print(_c('33', '  ! ') + msg)


def info(msg: str) -> None:
    print('    ' + msg)


class DeployError(Exception):
    pass


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)) or '.'
    except ValueError:
        return str(path)


def run(cmd: list, *, cwd: Path | None = None, env: dict | None = None,
        capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, streaming its output unless `capture`. Only the command
    is echoed — never environment values (the DB password travels there)."""
    shown = ' '.join(str(c) for c in cmd)
    info(_c('2', f'$ {shown}' + (f'   (in {_display_path(cwd)})' if cwd else '')))
    result = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, text=True, capture_output=capture)
    if check and result.returncode != 0:
        if capture:
            sys.stdout.write(result.stdout or '')
            sys.stderr.write(result.stderr or '')
        raise DeployError(f'Command failed ({result.returncode}): {shown}')
    return result


def manage(*args: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    return run([VENV_PY, 'manage.py', *args], cwd=BACKEND, capture=capture, check=check)


# ── Environment ───────────────────────────────────────────────────────────────

def read_env_file() -> dict[str, str]:
    """Minimal .env parser (KEY=VALUE, # comments, optional quotes)."""
    values: dict[str, str] = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
            value = value[1:-1]
        values[key.strip()] = value
    return values


def node_env() -> tuple[dict, str]:
    """PATH with a usable yarn/node (nvm installs aren't on root's non-login PATH)."""
    env = os.environ.copy()
    yarn = shutil.which('yarn')
    if not yarn:
        candidates = sorted((Path.home() / '.nvm' / 'versions' / 'node').glob('*/bin/yarn'), reverse=True)
        if candidates:
            yarn = str(candidates[0])
            env['PATH'] = f'{candidates[0].parent}:{env.get("PATH", "")}'
    if not yarn:
        raise DeployError('yarn not found (checked PATH and ~/.nvm).')
    return env, yarn


# ── Steps ─────────────────────────────────────────────────────────────────────

def preflight(args) -> dict:
    step('Preflight')
    if os.geteuid() != 0 and not args.dry_run and not args.skip_restart:
        raise DeployError('Run as root (needed for systemctl restart), or pass --skip-restart.')
    if not VENV_PY.exists():
        raise DeployError(f'Backend virtualenv not found at {VENV_PY}.')
    if not ENV_FILE.exists():
        raise DeployError(f'{ENV_FILE} is missing — the service reads its settings from it.')
    ok(f'virtualenv: {VENV_PY}')

    commit = run(['git', 'rev-parse', '--short', 'HEAD'], cwd=REPO, capture=True).stdout.strip()
    branch = run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=REPO, capture=True).stdout.strip()
    ok(f'repository at {branch} @ {commit}')
    dirty = run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPO, capture=True).stdout.strip()
    if dirty:
        warn('working tree has uncommitted changes to tracked files — they will be deployed as-is:')
        for line in dirty.splitlines()[:15]:
            info(line)
    if branch != 'main':
        warn(f'deploying from branch "{branch}", not main')

    env = read_env_file()
    if env.get('DEBUG', '').lower() in ('1', 'true', 'yes'):
        warn('.env has DEBUG=True — not a production configuration')

    manage('check')
    ok('Django system check passed')

    result = manage('makemigrations', '--check', '--dry-run', capture=True, check=False)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        raise DeployError('Model changes without migrations — run makemigrations, review, and commit them first.')
    ok('no missing migrations')

    if shutil.which('nginx'):
        nginx = run(['nginx', '-t'], capture=True, check=False)
        if nginx.returncode == 0:
            ok('nginx configuration valid')
        else:
            warn('nginx -t failed (the app restart does not touch nginx, but check it):')
            info((nginx.stderr or '').strip().splitlines()[-1] if nginx.stderr else '')
    return {'commit': commit, 'branch': branch, 'env': env}


def git_pull(args) -> None:
    step('Update code')
    if args.dry_run:
        info('would run: git pull --ff-only')
        return
    run(['git', 'pull', '--ff-only'], cwd=REPO)
    ok('pulled')


def install_deps(args) -> None:
    step('Dependencies')
    if args.dry_run:
        info('would run: pip install -r requirements.txt')
        if not args.skip_frontend:
            info('would run: yarn install --frozen-lockfile')
        return
    run([VENV_PY, '-m', 'pip', 'install', '-q', '--disable-pip-version-check', '-r', 'requirements.txt'], cwd=BACKEND)
    ok('Python requirements satisfied')
    if not args.skip_frontend:
        env, yarn = node_env()
        run([yarn, 'install', '--frozen-lockfile', '--silent'], cwd=FRONTEND_SRC, env=env)
        ok('Node packages installed')


def build_frontend(args) -> None:
    step('Frontend build')
    env, yarn = node_env()
    if args.site_url:
        env['VITE_SITE_URL'] = args.site_url
    if args.dry_run:
        info(f'would run: {yarn} build, swap dist/ into {FRONTEND_LIVE.relative_to(REPO)}, collectstatic')
        return
    run([yarn, 'build'], cwd=FRONTEND_SRC, env=env)
    index = FRONTEND_DIST / 'index.html'
    if not index.exists():
        raise DeployError('Build finished but dist/index.html is missing.')
    ok('built')


def swap_frontend(args) -> None:
    """Copy dist/ next to the live dir, then rename into place (the old build
    goes to .deploy/frontend.prev). Django caches the index.html template, so
    the running workers keep serving the old page until the restart."""
    step('Install frontend build')
    if args.dry_run:
        info('would swap the SPA build and run collectstatic --noinput')
        return
    STATE_DIR.mkdir(exist_ok=True)
    staging = FRONTEND_LIVE.with_name('frontend.new')
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(FRONTEND_DIST, staging)
    if FRONTEND_PREV.exists():
        shutil.rmtree(FRONTEND_PREV)
    if FRONTEND_LIVE.exists():
        FRONTEND_LIVE.rename(FRONTEND_PREV)
    staging.rename(FRONTEND_LIVE)
    ok(f'SPA installed (previous build kept in {FRONTEND_PREV.relative_to(REPO)})')
    manage('collectstatic', '--noinput', '-v', '0')
    ok('static files collected')


def pending_migrations() -> list[str]:
    result = manage('migrate', '--plan', capture=True)
    lines = [l.rstrip() for l in result.stdout.splitlines() if l.strip()]
    if any('No planned migration operations' in l for l in lines):
        return []
    # "Planned operations:" followed by "app.0006_name" headers and indented ops.
    return [l for l in lines if re.match(r'^[a-z_]+\.\d{4}_', l)]


def backup_database(args, env: dict) -> Path | None:
    url = os.environ.get('DATABASE_URL') or env.get('DATABASE_URL', '')
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S')
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    # Dumps contain citizens' personal data: owner-only, always.
    STATE_DIR.chmod(0o700)
    BACKUP_DIR.chmod(0o700)
    os.umask(0o077)
    parsed = urlparse(url)

    if parsed.scheme.startswith('postgres'):
        if not shutil.which('pg_dump'):
            raise DeployError('pg_dump not found — install it or pass --no-backup.')
        target = BACKUP_DIR / f'gunaso-{stamp}.dump'
        pg_env = os.environ.copy()
        if parsed.password:
            pg_env['PGPASSWORD'] = unquote(parsed.password)  # never on the command line
        cmd = [
            'pg_dump', '--format=custom', '--no-owner', f'--file={target}',
            f'--host={parsed.hostname or "localhost"}', f'--port={parsed.port or 5432}',
            f'--username={unquote(parsed.username or "")}', parsed.path.lstrip('/'),
        ]
        run(cmd, env=pg_env)
    elif parsed.scheme == 'sqlite' or not url:
        db_path = Path(parsed.path) if url else BACKEND / 'db.sqlite3'
        target = BACKUP_DIR / f'gunaso-{stamp}.sqlite3'
        shutil.copy2(db_path, target)
    else:
        raise DeployError(f'Unsupported DATABASE_URL scheme "{parsed.scheme}" — pass --no-backup to skip.')

    target.chmod(0o600)
    size_mb = target.stat().st_size / 1_048_576
    ok(f'database backed up to {target.relative_to(REPO)} ({size_mb:.1f} MB)')

    backups = sorted(BACKUP_DIR.glob('gunaso-*'), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[KEEP_BACKUPS:]:
        old.unlink()
    return target


def migrate(args, env: dict) -> Path | None:
    step('Database migrations')
    pending = pending_migrations()
    if not pending:
        ok('database is up to date')
        return None
    info('pending:')
    for name in pending:
        info(f'  • {name}')
    if args.dry_run:
        info('would back up the database, then run: migrate --noinput')
        return None
    backup = None
    if args.no_backup:
        warn('skipping backup (--no-backup)')
    else:
        backup = backup_database(args, env)
    manage('migrate', '--noinput')
    ok(f'applied {len(pending)} migration(s)')
    return backup


def restart_service(args) -> None:
    step(f'Restart {args.service}')
    if args.dry_run or args.skip_restart:
        info(f'would run: systemctl restart {args.service}')
        return
    run(['systemctl', 'restart', args.service])
    deadline = time.time() + 30
    while time.time() < deadline:
        state = run(['systemctl', 'is-active', args.service], capture=True, check=False).stdout.strip()
        if state == 'active' and Path(args.socket).exists():
            ok(f'{args.service} is active')
            return
        if state == 'failed':
            break
        time.sleep(1)
    run(['journalctl', '-u', args.service, '-n', '40', '--no-pager'], check=False)
    raise DeployError(f'{args.service} did not become active.')


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float = 10):
        super().__init__('localhost', timeout=timeout)
        self._path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._path)


def socket_get(sock_path: str, path: str, host: str) -> tuple[int, str]:
    conn = UnixHTTPConnection(sock_path)
    # X-Forwarded-Proto mirrors nginx, so SECURE_SSL_REDIRECT doesn't 301 us.
    conn.request('GET', path, headers={'Host': host, 'X-Forwarded-Proto': 'https'})
    resp = conn.getresponse()
    body = resp.read().decode('utf-8', 'replace')
    conn.close()
    return resp.status, body


def verify(args, env: dict) -> None:
    step('Verify')
    if args.dry_run or args.skip_restart:
        info('skipped (no restart performed)')
        return
    host = (env.get('ALLOWED_HOSTS', 'localhost').split(',')[0] or 'localhost').strip()

    last_error = ''
    for _ in range(10):  # workers may still be booting
        try:
            status, body = socket_get(str(args.socket), '/api/v1/health/', host)
            if status == 200 and json.loads(body).get('status') == 'ok':
                ok('API health check: database reachable')
                break
            last_error = f'HTTP {status}: {body[:200]}'
        except (OSError, ValueError) as exc:
            last_error = str(exc)
        time.sleep(1.5)
    else:
        raise DeployError(f'Health check failed: {last_error}')

    status, body = socket_get(str(args.socket), '/', host)
    if status != 200 or 'id="app"' not in body:
        raise DeployError(f'SPA index not served correctly (HTTP {status}).')
    ok('SPA index served')

    assets = re.findall(r'/static/(assets/[^"\']+\.(?:js|css))', body)
    missing = [a for a in assets if not (STATIC_ROOT / a).exists()]
    if missing:
        raise DeployError(f'Built assets missing from STATIC_ROOT: {missing[:3]} — did collectstatic run?')
    ok(f'{len(assets)} referenced asset(s) present in STATIC_ROOT')

    if args.public_url:
        url = args.public_url.rstrip('/') + '/api/v1/health/'
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                ok(f'public URL healthy: {url} (HTTP {resp.status})')
        except (urllib.error.URLError, OSError) as exc:
            warn(f'public URL check failed ({url}): {exc} — the socket checks passed, so check nginx/DNS/TLS')


def rollback_frontend(args) -> None:
    step('Roll back frontend')
    if not FRONTEND_PREV.exists():
        raise DeployError('No previous frontend build in .deploy/frontend.prev.')
    if args.dry_run:
        info('would restore .deploy/frontend.prev, collectstatic, restart')
        return
    broken = FRONTEND_LIVE.with_name('frontend.rolledback')
    if broken.exists():
        shutil.rmtree(broken)
    if FRONTEND_LIVE.exists():
        FRONTEND_LIVE.rename(broken)
    shutil.copytree(FRONTEND_PREV, FRONTEND_LIVE)
    shutil.rmtree(broken, ignore_errors=True)
    ok('previous SPA build restored')
    manage('collectstatic', '--noinput', '-v', '0')


def record(result: str, meta: dict, started: float, backup: Path | None) -> None:
    STATE_DIR.mkdir(exist_ok=True)
    line = (
        f'{dt.datetime.now().isoformat(timespec="seconds")}  {result:<8}  '
        f'{meta.get("branch", "?")}@{meta.get("commit", "?")}  {time.time() - started:.0f}s'
        + (f'  backup={backup.name}' if backup else '')
    )
    with HISTORY.open('a') as fh:
        fh.write(line + '\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pull', action='store_true', help='git pull --ff-only before deploying')
    parser.add_argument('--dry-run', action='store_true', help='run read-only checks and show what would happen')
    parser.add_argument('--skip-deps', action='store_true', help='skip pip/yarn installs')
    parser.add_argument('--skip-frontend', action='store_true', help='do not rebuild the SPA')
    parser.add_argument('--skip-restart', action='store_true', help='do not restart the service (and skip verification)')
    parser.add_argument('--no-backup', action='store_true', help='do not back up the database before migrating')
    parser.add_argument('--rollback-frontend', action='store_true', help='restore the previous SPA build and restart')
    parser.add_argument('--service', default=DEFAULT_SERVICE, help=f'systemd unit (default {DEFAULT_SERVICE})')
    parser.add_argument('--socket', default=str(DEFAULT_SOCKET), help='gunicorn unix socket to health-check')
    parser.add_argument('--public-url', default='https://gunaaso.com', help='public origin to check after deploy ("" to skip)')
    parser.add_argument('--site-url', default='', help='VITE_SITE_URL for social-card URLs (default: vite.config.js)')
    args = parser.parse_args()

    started = time.time()
    meta: dict = {}
    backup = None
    print(_c('1', f'Gunaso deploy — {dt.datetime.now():%Y-%m-%d %H:%M:%S}' + ('  [DRY RUN]' if args.dry_run else '')))
    try:
        if args.rollback_frontend:
            meta = preflight(args)
            rollback_frontend(args)
            restart_service(args)
            verify(args, meta['env'])
            if not args.dry_run:
                record('ROLLBACK', meta, started, None)
            print('\n' + _c('1;32', 'Frontend rolled back.'))
            return 0

        if args.pull:
            git_pull(args)
        meta = preflight(args)
        if not args.skip_deps:
            install_deps(args)
        if not args.skip_frontend:
            build_frontend(args)
            swap_frontend(args)
        backup = migrate(args, meta['env'])
        restart_service(args)
        verify(args, meta['env'])
    except DeployError as exc:
        print('\n' + _c('1;31', f'✗ Deploy failed: {exc}'))
        if backup:
            print(_c('33', f'  A pre-migration backup exists: {backup}'))
            print(_c('33', '  Restore (only if needed): pg_restore --clean --no-owner -d <database> ' + str(backup)))
        if FRONTEND_PREV.exists():
            print(_c('33', '  Previous SPA build: python3 scripts/deploy.py --rollback-frontend'))
        if not args.dry_run and meta:
            record('FAILED', meta, started, backup)
        return 1
    except KeyboardInterrupt:
        print('\n' + _c('1;31', 'Interrupted.'))
        return 130

    if args.dry_run:
        print('\n' + _c('1;32', 'Dry run complete — nothing was changed.'))
    else:
        record('OK', meta, started, backup)
        print('\n' + _c('1;32', f'Deployed {meta["branch"]}@{meta["commit"]} in {time.time() - started:.0f}s.'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
