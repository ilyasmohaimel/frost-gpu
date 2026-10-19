"""Record only the inspected, owned XWayland Brave window on this laptop."""
import subprocess,time,pathlib,argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--window",required=True)
parser.add_argument("--pid",required=True)
args=parser.parse_args()
window=args.window;expected_pid=args.pid
if subprocess.check_output(['xdotool','getwindowpid',window],text=True).strip()!=expected_pid:raise SystemExit('Window ownership changed')
if 'frost-gpu' not in subprocess.check_output(['xdotool','getwindowname',window],text=True):raise SystemExit('Window title changed')
out=pathlib.Path(__file__).resolve().parents[1]/'composition/assets/desktop/repo-screen.mp4'
with (out.parent/'record.log').open('w') as log:
 proc=subprocess.Popen(['ffmpeg','-v','warning','-y','-f','x11grab','-framerate','30','-window_id',window,'-draw_mouse','0','-i',':0','-t','6','-vf','crop=1920:1040:16:10,pad=1920:1080:0:20:color=0x0d1117','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(out)],stdout=log,stderr=log)
 time.sleep(.8)
 subprocess.run(['xdotool','mousemove','--window',window,'1060','650'],check=True)
 for _ in range(6):
  if subprocess.check_output(['xdotool','getactivewindow'],text=True).strip()!=window:proc.terminate();raise SystemExit('Focus changed during owned recording')
  subprocess.run(['xdotool','click','5'],check=True);time.sleep(.35)
 code=proc.wait()
 if code:raise SystemExit(f'Capture failed: {code}')
print('Real laptop window recording saved',out)
