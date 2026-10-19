"""Select the settled hero poster, bake frame zero and verify the delivery."""
from pathlib import Path
import hashlib
import io
import json
import subprocess
from PIL import Image, ImageChops, ImageStat

root = Path(__file__).resolve().parents[1]
raw = root / 'brag-render.mp4'
poster = root / 'brag.jpg'
staging = root / 'brag-staging.mp4'
final = root / 'brag.mp4'


def run(*args):
    subprocess.run(args, check=True)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format',
        '-of', 'json', str(path)
    ], text=True))


source_hash = hashlib.sha256(b''.join((root / 'production' / name).read_bytes()
                                     for name in ['matched_model.py', 'board_detail.py'])).hexdigest()
assert json.loads((root / 'asset-render-manifest.json').read_text())['cut']['sourceSha256'] == source_hash
raw_metadata = probe(raw)
video = next(s for s in raw_metadata['streams'] if s['codec_type'] == 'video')
assert (video['width'], video['height'], video['nb_read_frames'], video['avg_frame_rate']) == (1920, 1080, '1440', '60/1')
run('ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-threads', '2',
    '-ss', '22.6', '-i', str(raw), '-frames:v', '1', '-q:v', '2', str(poster))
run('ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning', '-filter_complex_threads', '2',
    '-threads', '2', '-i', str(raw), '-i', str(poster),
    '-filter_complex', "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]",
    '-map', '[v]', '-map', '0:a?', '-c:v', 'libx264', '-crf', '16', '-preset', 'slow',
    '-threads', '2', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-frames:v', '1440',
    '-movflags', '+faststart', '-progress', 'pipe:1', str(staging))
metadata = probe(staging)
video = next(s for s in metadata['streams'] if s['codec_type'] == 'video')
audio = next(s for s in metadata['streams'] if s['codec_type'] == 'audio')
assert (video['width'], video['height'], video['nb_read_frames'], video['avg_frame_rate']) == (1920, 1080, '1440', '60/1')
assert abs(float(video['duration']) - 24) < .02
first_frame = subprocess.check_output([
    'ffmpeg', '-v', 'error', '-threads', '2', '-i', str(staging),
    '-frames:v', '1', '-f', 'image2pipe', '-c:v', 'png', 'pipe:1'
])
with Image.open(io.BytesIO(first_frame)) as first, Image.open(poster) as selected:
    poster_error = ImageStat.Stat(ImageChops.difference(first.convert('RGB'), selected.convert('RGB'))).mean
assert max(poster_error) < 4, ('First frame does not match the selected poster', poster_error)
run('ffmpeg', '-v', 'error', '-threads', '2', '-i', str(staging), '-f', 'null', '-')
staging.replace(final)
metadata['verification'] = {'decodedAllFrames': True, 'posterTimeSeconds': 22.6,
                            'posterBakedIntoFrameZero': True, 'sourceSha256': source_hash,
                            'posterMeanAbsoluteError': poster_error,
                            'sha256': hashlib.sha256(final.read_bytes()).hexdigest()}
(root / 'final-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
print('Final delivery verified: 24 seconds, 1920x1080, 60 fps, audio included', flush=True)
