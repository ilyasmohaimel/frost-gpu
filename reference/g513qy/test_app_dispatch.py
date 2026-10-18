import tempfile
import unittest
from unittest.mock import patch
import frost_app as f

class Dispatch(unittest.TestCase):
    def test_stock_keeps_exact_original_command(self):
        args=['env','APP_OPTION=a b','chatgpt','url with spaces']
        command,env=f.plan('codex',args,{'USER_FLAG':'yes'},enabled=False)
        self.assertEqual(command,args);self.assertEqual(env,{'USER_FLAG':'yes'})

    def test_preserves_env_wrapper_without_shell_evaluation(self):
        command,env=f.plan('codex',['env','APP_OPTION=$(literal text)','chatgpt','url with spaces'],{},enabled=True)
        self.assertEqual(command,['/opt/frost-gpu/bin/zss-run','chatgpt','url with spaces','--use-angle=vulkan','--enable-features=Vulkan','--ozone-platform=x11'])
        self.assertEqual(env['APP_OPTION'],'$(literal text)')

    def test_env_options_do_not_get_reinterpreted(self):
        args=['env','-u','SOME_VARIABLE','brave']
        command,env=f.plan('brave',args,{},enabled=True)
        self.assertEqual(command,args)
        args=['env','--','APP_OPTION=a','brave']
        command,env=f.plan('brave',args,{},enabled=True)
        self.assertEqual(command,args)

    def test_terminal_config_and_argv_preserved(self):
        command,env=f.plan('wezterm',['wezterm','start','--cwd','a b'],{},enabled=True)
        self.assertEqual(command,['/opt/frost-gpu/bin/zss-run','--gl','wezterm','--config','front_end="OpenGL"','--config','enable_wayland=false','start','--always-new-process','--cwd','a b'])
        self.assertEqual(env['GDK_BACKEND'],'x11')

    def test_original_security_wrapper_remains(self):
        command,env=f.plan('bitwarden',['bitwarden-desktop','safe argument'],{'LD_PRELOAD':'security-library'},enabled=True)
        self.assertEqual(command,['/opt/frost-gpu/bin/zss-run','bitwarden-desktop','safe argument','--use-angle=vulkan','--enable-features=Vulkan','--ozone-platform=x11'])
        self.assertEqual(env['LD_PRELOAD'],'security-library')
        self.assertNotIn('--no-sandbox',command)

    def test_unknown_workflows_default_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            for profile in ('firefox','vesktop','rootapp','spotify'):
                self.assertFalse(f.selected(profile,{'XDG_CONFIG_HOME':tmp}))
            self.assertTrue(f.selected('brave',{'XDG_CONFIG_HOME':tmp}))

    def test_chromium_feature_merge_and_explicit_platform(self):
        args=['codium','--enable-features=Example','--ozone-platform=x11']
        command,env=f.plan('codium',args,{},enabled=True)
        self.assertIn('--enable-features=Example,Vulkan',command)
        self.assertEqual(command.count('--ozone-platform=x11'),1)
        self.assertIn('--use-angle=vulkan',command)

    def test_child_launcher_cleans_only_our_inherited_driver(self):
        inherited={'FROST_GPU_WRAPPED':'1','VK_DRIVER_FILES':'/opt/frost-gpu/share/zss_icd.json','MESA_LOADER_DRIVER_OVERRIDE':'zink','QSG_RHI_BACKEND':'vulkan','FROST_GPU_WAYLAND_DISPLAY':'wayland-test','ZSS_SOCKET':'keep-this-socket','LD_PRELOAD':'security-wrapper'}
        command,env=f.plan('brave',['brave'],inherited,enabled=False)
        self.assertEqual(command,['brave'])
        self.assertNotIn('VK_DRIVER_FILES',env)
        self.assertNotIn('MESA_LOADER_DRIVER_OVERRIDE',env)
        self.assertNotIn('QSG_RHI_BACKEND',env)
        self.assertEqual(env['WAYLAND_DISPLAY'],'wayland-test')
        self.assertEqual(env['ZSS_SOCKET'],'keep-this-socket')
        self.assertEqual(env['LD_PRELOAD'],'security-wrapper')
        command,env=f.plan('brave',['brave'],{'VK_DRIVER_FILES':'/a/user/explicit-driver.json'},enabled=False)
        self.assertEqual(env['VK_DRIVER_FILES'],'/a/user/explicit-driver.json')

    def test_priority_apps_use_tested_presentation(self):
        command,env=f.plan('rog',['rog-control-center','--autostart','--background'],{'WAYLAND_DISPLAY':'original'},enabled=True)
        self.assertEqual(command,['/opt/frost-gpu/bin/zss-run','--gl','/opt/frost-gpu/bin/rog-control-center','--autostart','--background'])
        self.assertEqual(env['WINIT_UNIX_BACKEND'],'x11')
        self.assertNotIn('WAYLAND_DISPLAY',env)
        command,env=f.plan('wechat',['/opt/wechat/wechat','file'],{},enabled=True)
        self.assertEqual(env['QT_QPA_PLATFORM'],'xcb')
        self.assertEqual(command[-1],'file')

    def test_battery_new_launch_uses_igpu(self):
        with patch.object(f.session,'ac_online',return_value=False):
            command,env=f.plan('brave',['brave'],{},enabled=True)
            self.assertEqual(env['ZSS_START_ON'],f.session.IGPU)

    def test_wechat_native_fallback_does_not_load_migration_layer(self):
        inherited={'FROST_GPU_WRAPPED':'1','VK_DRIVER_FILES':'/opt/frost-gpu/share/zss_icd.json','GALLIUM_DRIVER':'zink'}
        command,env=f.plan('wechat',['/opt/wechat/wechat','a file'],inherited,enabled=True)
        self.assertEqual(command,['/opt/wechat/wechat','a file'])
        self.assertNotIn('VK_DRIVER_FILES',env);self.assertNotIn('GALLIUM_DRIVER',env)
        self.assertEqual(env['MESA_VK_DEVICE_SELECT'],'1002:1638!')
        self.assertEqual(env['FROST_GPU_FIXED_IGPU'],'1')
        command,child=f.plan('brave',['brave'],env,enabled=False)
        self.assertEqual(child['MESA_VK_DEVICE_SELECT'],'1002:1638')
        self.assertEqual(child['MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE'],'0')
        self.assertNotIn('FROST_GPU_FIXED_IGPU',child)

    def test_office_uses_native_tested_backend_without_graphics_interposer(self):
        command,env=f.plan('libreoffice',['libreoffice','--impress','file with spaces'],
            {'FROST_GPU_WRAPPED':'1','VK_DRIVER_FILES':'/opt/frost-gpu/share/zss_icd.json'},enabled=True)
        self.assertEqual(command,['libreoffice','--impress','file with spaces'])
        self.assertEqual(env['SAL_USE_VCLPLUGIN'],'gtk3');self.assertEqual(env['GDK_BACKEND'],'x11')
        self.assertNotIn('VK_DRIVER_FILES',env)

if __name__=='__main__':unittest.main()
