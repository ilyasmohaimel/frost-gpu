"""Run an owned media process with fail-closed thermal and profile checks.

This is an additional operational cutoff, not hardware thermal protection.
It changes no clocks, voltage, fan curves or system power limits.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def monitor_paths():
    roots = list(Path('/sys/class/hwmon').glob('hwmon*'))
    cpu = next(p for p in roots if (p / 'name').read_text().strip() == 'k10temp')
    gpu = next(p for p in roots if (p / 'name').read_text().strip() == 'amdgpu'
               and (p / 'device').resolve().name == '0000:03:00.0')
    asus = next(p for p in roots if (p / 'name').read_text().strip() == 'asus')
    return {'cpu': cpu / 'temp1_input', 'edge': gpu / 'temp1_input',
            'junction': gpu / 'temp2_input', 'memory': gpu / 'temp3_input',
            'gpu_fan': asus / 'fan2_input'}


def sample(paths):
    row = {k: int(p.read_text()) / (1 if k == 'gpu_fan' else 1000)
           for k, p in paths.items()}
    row['profile'] = Path('/sys/firmware/acpi/platform_profile').read_text().strip()
    row['barrel_ac'] = Path('/sys/class/power_supply/ADP0/online').read_text().strip() == '1'
    return row


def unsafe(row):
    if row['profile'] != 'performance' or not row['barrel_ac']:
        return 'Performance profile or barrel power lost'
    # AMD specifies 105 C Tjmax for the 5900HX. Keep this job's CPU cutoff
    # ten degrees below that. RX is stopped at 90 C, below its reported
    # 100 C critical limit; a full-speed GPU curve is requested for this render.
    # https://www.amd.com/en/support/downloads/drivers.html/processors/ryzen/ryzen-5000-series/amd-ryzen-9-5900hx.html
    for key, limit in [('cpu', 95), ('edge', 90), ('junction', 90), ('memory', 90)]:
        if row[key] >= limit:
            return f'{key} reached cutoff {limit} C'
    if max(row['edge'], row['junction']) >= 68 and row['gpu_fan'] < 500:
        return 'GPU is warm but ASUS fan tachometer is below 500 RPM'
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', type=Path, required=True)
    ap.add_argument('--timeout', type=float, default=600)
    ap.add_argument('command', nargs=argparse.REMAINDER)
    args = ap.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        ap.error('a command is required')
    paths = monitor_paths()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open('x', buffering=1) as log:
        def record(event, **data):
            log.write(json.dumps({'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  'event': event, **data}) + '\n')
        initial = sample(paths)
        record('preflight', **initial)
        reason = unsafe(initial)
        if reason:
            raise SystemExit('Preflight refused: ' + reason)
        child = subprocess.Popen(command, start_new_session=True)
        record('started', pid=child.pid)
        started = time.monotonic()
        try:
            while child.poll() is None:
                row = sample(paths)
                record('sample', **row)
                reason = unsafe(row)
                if time.monotonic() - started >= args.timeout:
                    reason = 'Maximum batch runtime exceeded'
                if reason:
                    raise RuntimeError(reason)
                time.sleep(1)
            record('completed', returncode=child.returncode)
            return child.returncode
        except BaseException as exc:
            record('aborted', reason=str(exc))
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
            raise


if __name__ == '__main__':
    raise SystemExit(main())
