"""Restore only the GPU curve temporarily changed for this film render."""
import datetime
import json
from pathlib import Path
import re
import subprocess

backup = Path(__file__).resolve().parent / 'runlogs/rx-fan-restore.json'
saved = json.loads(backup.read_text())


def profile():
    content = Path('/etc/asusd/fan_curves.ron').read_text()
    block = re.search(r'performance: \[(.*?)\],\s*quiet:', content, re.S).group(1)
    gpu = re.search(r'fan: GPU,\s*pwm: \((.*?)\),\s*temp: \((.*?)\),\s*enabled: (true|false)', block, re.S)
    pwm = [int(x.strip()) for x in gpu[1].split(',') if x.strip()]
    temperatures = [int(x.strip()) for x in gpu[2].split(',') if x.strip()]
    cpu = re.search(r'fan: CPU,.*?enabled: (true|false)', block, re.S).group(0)
    return ','.join(f'{t}c:{v}' for t, v in zip(temperatures, pwm)), gpu[3] == 'true', cpu


current, enabled, cpu_before = profile()
if current != saved['renderData']:
    raise SystemExit('GPU curve changed elsewhere; preserving it instead of overwriting it')
base = ['asusctl', 'fan-curve', '--mod-profile', 'performance', '--fan', 'gpu']
subprocess.run(base + ['--data', saved['originalData']], check=True, capture_output=True)
subprocess.run(base + ['--enable-fan-curve', str(saved['enabled']).lower()], check=True, capture_output=True)
data_after, enabled_after, cpu_after = profile()
assert data_after == saved['originalData'] and enabled_after == saved['enabled']
assert cpu_before == cpu_after
saved['restoredAt'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
backup.write_text(json.dumps(saved, indent=2) + '\n')
print('Original Performance GPU curve restored; CPU curve preserved')
