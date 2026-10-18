"""Fail-closed startup routing, real device enumeration, and stock recovery."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import frost_session as f


class Routing(unittest.TestCase):
    def test_stock_route_preserves_arguments(self):
        for mode, binary in [('kwin-wrapper','kwin_wayland_wrapper'),('kwin','kwin_wayland'),('plasma','plasmashell')]:
            argv, env = f.plan(mode,['--example','a b'], {'PATH':'/usr/bin'}, enabled=False)
            self.assertEqual(argv, ['/usr/bin/'+binary,'--example','a b'])
            self.assertNotIn('QT_PLUGIN_PATH', env)

    def test_wrapper_has_only_private_child_dispatch(self):
        argv, env = f.plan('kwin-wrapper',['--xwayland'], {'PATH':'/usr/bin'}, enabled=True)
        self.assertEqual(argv[0],'/opt/frost-gpu/kwin/bin/kwin_wayland_wrapper')
        self.assertEqual(env['PATH'],f.DISPATCH+':/usr/bin')
        self.assertNotIn('QT_PLUGIN_PATH', env)

    def test_kwin_crash_selects_stock_and_persists_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={'XDG_RUNTIME_DIR':tmp,'KWIN_RESTART_COUNT':'1','QT_PLUGIN_PATH':'/opt/frost-gpu/kwin/lib/plugins:/usr/lib/qt6/plugins','KWIN_ENABLE_EXPERIMENTAL_GPU_SWITCH':'1'}
            argv, result=f.plan('kwin',['--wayland-fd','4'],env,enabled=True)
            self.assertEqual(argv,['/usr/bin/kwin_wayland','--wayland-fd','4'])
            self.assertEqual(result['QT_PLUGIN_PATH'],'/usr/lib/qt6/plugins')
            self.assertNotIn('KWIN_ENABLE_EXPERIMENTAL_GPU_SWITCH',result)
            self.assertTrue((f.runtime(env)/'fallback').is_file())
            self.assertFalse(f.opted_in({**env,f.FLAG:'1'}))

    def test_plasma_uses_vulkan_not_global_qt_override(self):
        env={'PATH':'/usr/bin','ZSS_SOCKET':'/private/socket'}
        argv,result=f.plan('plasma',['--no-respawn'],env,enabled=True,daemon_ready=True)
        self.assertEqual(argv,['/opt/frost-gpu/bin/zss-run','/usr/bin/plasmashell','--no-respawn'])
        self.assertEqual(result['QSG_RHI_BACKEND'],'vulkan')
        self.assertNotIn('QSG_RHI_BACKEND',env)
        self.assertEqual(result['ZSS_RETAIN'],'ram')

    def test_missing_daemon_uses_stock_plasma(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv, env=f.plan('plasma',['--no-respawn'],{'XDG_RUNTIME_DIR':tmp},enabled=True,daemon_ready=False)
            self.assertEqual(argv[0],'/usr/bin/plasmashell')
            self.assertTrue((f.runtime(env)/'fallback').exists())

    def test_disabled_file_and_missing_optin(self):
        with tempfile.TemporaryDirectory() as tmp:
            env={f.FLAG:'1','XDG_CONFIG_HOME':tmp,'XDG_RUNTIME_DIR':tmp,'XDG_SESSION_ID':'test123'}
            f.mark_login(env)
            self.assertTrue(f.opted_in(env))
            self.assertFalse(f.opted_in({**env,'XDG_SESSION_ID':'other123'}))
            p=Path(tmp)/'frost-gpu-live/disabled';p.parent.mkdir(exist_ok=True);p.touch()
            self.assertFalse(f.opted_in(env))
        self.assertFalse(f.opted_in({}))

    @unittest.skipUnless(os.environ.get("FROST_TEST_HARDWARE") == "1", "requires reference DRM hardware")
    def test_real_both_devices_remain_visible_on_battery(self):
        env=f.session_environment({'XDG_RUNTIME_DIR':'/run/user/1000','MESA_VK_DEVICE_SELECT':'1002:1638!'}, ac=False)
        self.assertEqual(len(env['KWIN_DRM_DEVICES'].split(':')),2)
        self.assertEqual(len(env['KWIN_RENDER_NODES'].split(':')),2)
        self.assertEqual(env['KWIN_XWAYLAND_RENDER_DEVICE'],os.path.realpath('/dev/dri/by-path/pci-'+f.IGPU+'-render'))
        self.assertEqual(env['MESA_VK_DEVICE_SELECT'],'1002:1638')
        self.assertEqual(env['MESA_VK_DEVICE_SELECT_FORCE_DEFAULT_DEVICE'],'0')
        self.assertEqual(env[f.FLAG],'1')

    @unittest.skipUnless(os.environ.get("FROST_TEST_HARDWARE") == "1", "requires reference DRM hardware")
    def test_ac_renderer_is_rx_but_sync_device_stays_on_igpu(self):
        env=f.session_environment({'XDG_RUNTIME_DIR':'/run/user/1000'}, ac=True)
        self.assertEqual(env['KWIN_DRM_DEVICES'].split(':')[0],os.path.realpath('/dev/dri/by-path/pci-'+f.RX+'-card'))
        self.assertEqual(env['KWIN_RENDER_NODES'].split(':')[0],os.path.realpath('/dev/dri/by-path/pci-'+f.IGPU+'-render'))
        self.assertEqual(set(env['KWIN_RENDER_NODES'].split(':')),{os.path.realpath('/dev/dri/by-path/pci-'+gpu+'-render')for gpu in (f.IGPU,f.RX)})

    def test_package_mismatch_refuses_custom_stack(self):
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp)
            (prefix / 'share').mkdir()
            (prefix / 'share/manifest.json').write_text('{"packages":{"kwin":"fixture-version"}}')
            for part in ('kwin/bin/kwin_wayland', 'kwin/bin/kwin_wayland_wrapper', 'bin/zss-run', 'bin/zssd', 'lib/libzss_airlock.so', 'kwin/lib/libkwin.so.6', 'kwin/lib/libexec/plasma-setup-xwayland'):
                file = prefix / part
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            with patch.object(f.subprocess, 'check_output', return_value='kwin fixture-version\n'):
                self.assertTrue(f.compatible(prefix))
            with patch.object(f.subprocess, 'check_output', return_value='kwin changed-version\n'):
                self.assertFalse(f.compatible(prefix))


if __name__=='__main__': unittest.main()
