"""Make a smooth camera push from the verified RX-rendered cutaway frame."""
from pathlib import Path
import hashlib
import json
import subprocess
import time
from PIL import Image

root = Path(__file__).resolve().parents[1]
assets = root / 'composition/assets/blender'
started = time.monotonic()
source = assets / 'cut-frames/frame-0001.png'
with Image.open(source) as image:
    assert image.size == (1920, 1080)
    image.verify()

staging = assets / 'cut-staging.webm'
subprocess.run([
    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning', '-filter_threads', '2',
    '-i', str(source),
    '-vf', "scale=3840:2160:flags=lanczos,zoompan=z='1+0.00015*on':"
           "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=300:s=1920x1080:fps=60,"
           'eq=gamma=1.08:saturation=.98',
    '-frames:v', '300', '-fps_mode', 'cfr', '-r', '60',
    '-c:v', 'libvpx-vp9', '-crf', '20', '-b:v', '0', '-row-mt', '1',
    '-tile-columns', '2', '-threads', '2', '-cpu-used', '3',
    '-pix_fmt', 'yuv420p', '-an', '-progress', 'pipe:1', str(staging)
], check=True)
metadata = json.loads(subprocess.check_output([
    'ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
    '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames',
    '-of', 'json', str(staging)
], text=True))['streams'][0]
assert (metadata['width'], metadata['height'], metadata['nb_read_frames']) == (1920, 1080, '300')
staging.replace(assets / 'cut.webm')
subprocess.run([
    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-threads', '2',
    '-i', str(assets / 'cut.webm'), '-frames:v', '1', '-c:v', 'libwebp',
    '-quality', '95', str(assets / 'cut-start.webp')
], check=True)
source_hash = hashlib.sha256(b''.join((root / 'production' / name).read_bytes()
                                     for name in ['matched_model.py', 'board_detail.py'])).hexdigest()
manifest_path = root / 'asset-render-manifest.json'
manifest = json.loads(manifest_path.read_text())
manifest['cut'] = {'frames': 300, 'fps': 60, 'elapsedSeconds': round(time.monotonic()-started, 1),
                   'sourceSha256': source_hash, 'metadata': metadata,
                   'technique': 'RX-rendered still with a centered 4.5 percent camera push',
                   'renderedFrame': 'frame-0001.png; inward-set blower edge exposed',
                   'frameSha256': hashlib.sha256(source.read_bytes()).hexdigest()}
projection = json.loads((root / 'production/cut-projection.json').read_text())[0]['points']
finish = {name: [round(960+(x-960)*1.045, 1), round(540+(y-540)*1.045, 1)]
          for name, (x, y) in projection.items()}
(root / 'production/cut-video-projection.json').write_text(json.dumps([
    {'frame': 1, 'points': projection}, {'frame': 300, 'points': finish}
], indent=2) + '\n')
temporary = manifest_path.with_suffix('.staging.json')
temporary.write_text(json.dumps(manifest, indent=2) + '\n')
temporary.replace(manifest_path)
print('Verified and committed cut.webm: 300 frames at 60 fps', flush=True)
