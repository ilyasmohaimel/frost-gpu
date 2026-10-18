import os
from pathlib import Path
import shutil
import subprocess
import unittest
BASE=Path(__file__).resolve().parent/'session-integration'
class ShellEnvironment(unittest.TestCase):
 def run_shell(self,shell,interactive,active):
  env={**os.environ,'FROST_GPU_LIVE_SESSION':'1'if active else'0','FROST_GPU_WRAPPED':'1','VK_DRIVER_FILES':'/opt/frost-gpu/share/zss_icd.json','MESA_LOADER_DRIVER_OVERRIDE':'zink','FROST_GPU_WAYLAND_DISPLAY':'wayland-fixture','ZSS_SOCKET':'fixture-socket','FROST_TEST_KEPT':'keep'}
  cleared=interactive and active
  check="import os; e=os.environ; assert ('VK_DRIVER_FILES'not in e)=="+str(cleared)+"; assert ('MESA_LOADER_DRIVER_OVERRIDE'not in e)=="+str(cleared)+"; assert e['ZSS_SOCKET']=='fixture-socket'and e['FROST_TEST_KEPT']=='keep'"
  if cleared:check+="; assert e['WAYLAND_DISPLAY']=='wayland-fixture'"
  import shlex
  if shell=='bash':
   args=['bash','--noprofile','--norc',('-ic'if interactive else'-c'),'. '+shlex.quote(str(BASE/'frost-gpu-interactive.sh'))+'; /usr/bin/python3 -c '+shlex.quote(check)]
  else:
   args=['fish','--no-config',*(['-i']if interactive else[]),'-c','source '+shlex.quote(str(BASE/'90-frost-gpu.fish'))+'; /usr/bin/python3 -c '+shlex.quote(check)]
  p=subprocess.run(args,env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(p.returncode,0,p.stderr)
 def test_native_command_does_not_inherit_interposer(self):
  env={**os.environ,'VK_DRIVER_FILES':'/opt/frost-gpu/share/zss_icd.json','MESA_LOADER_DRIVER_OVERRIDE':'zink','ZSS_SOCKET':'fixture-socket'}
  script=BASE.parent/'frost_manage.py'
  result=subprocess.run(['/usr/bin/python3','-I',str(script),'native','--','/usr/bin/python3','-c',"import os; assert 'VK_DRIVER_FILES'not in os.environ and 'MESA_LOADER_DRIVER_OVERRIDE'not in os.environ; assert os.environ['ZSS_SOCKET']=='fixture-socket'"],env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(result.returncode,0,result.stderr)
 def check_fixed_filter_cleanup(self,shell):
  import shlex
  env={**os.environ,'FROST_GPU_LIVE_SESSION':'1','FROST_GPU_WRAPPED':'1','FROST_GPU_FIXED_IGPU':'1','MESA_VK_DEVICE_SELECT':'1002:1638!','MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE':'1'}
  check="import os; assert os.environ['MESA_VK_DEVICE_SELECT']=='1002:1638'; assert os.environ['MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE']=='0'; assert 'FROST_GPU_FIXED_IGPU' not in os.environ"
  hook=BASE/('frost-gpu-interactive.sh'if shell=='bash'else'90-frost-gpu.fish')
  args=([shell,'--noprofile','--norc','-ic']if shell=='bash'else[shell,'--no-config','-i','-c'])+['source '+shlex.quote(str(hook))+'; /usr/bin/python3 -c '+shlex.quote(check)]
  r=subprocess.run(args,env=env,capture_output=True,text=True,timeout=5)
  self.assertEqual(r.returncode,0,r.stderr)
 def test_bash_fixed_igpu_child_regains_both_devices(self):self.check_fixed_filter_cleanup('bash')
 @unittest.skipUnless(shutil.which('fish'),'Fish not installed')
 def test_fish_fixed_igpu_child_regains_both_devices(self):self.check_fixed_filter_cleanup('fish')
 def test_bash_interactive_frost_is_clean(self):self.run_shell('bash',True,True)
 def test_bash_stock_keeps_explicit_environment(self):self.run_shell('bash',True,False)
 def test_noninteractive_launcher_keeps_graphics_environment(self):self.run_shell('bash',False,True)
 @unittest.skipUnless(shutil.which('fish'),'Fish not installed')
 def test_fish_interactive_frost_is_clean(self):self.run_shell('fish',True,True)
if __name__=='__main__':unittest.main()
