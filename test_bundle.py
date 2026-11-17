"""Portable checks for standalone configuration and payload boundaries."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent

class BundleChecks(unittest.TestCase):
    def test_setup_handoff_restarts_only_launcher_processes(self):
        import run_stock_launcher as runner
        with tempfile.TemporaryDirectory() as folder:
            data=Path(folder).resolve(); prefix=data/'prefix'; wine=data/'wine'; server=data/'wineserver'
            install=prefix/'drive_c/Program Files (x86)/Innova/4game_global'
            (install/'bin').mkdir(parents=True)
            for file in (wine,server,install/'Inn.games.exe',install/'bin/Launcher.exe'):file.touch()
            config=data/'config.local.json'
            config.write_text(json.dumps(dict(prefix=str(prefix),wine=str(wine),wineserver=str(server),library_paths=[])))
            switch=data/'App With Spaces.txt';switch.write_text('disable-gpu\n')
            with patch.object(runner,'CONFIG',config),patch.object(runner,'DATA',data),patch.object(runner,'HELPERS',data/'absent-helpers'),patch.object(sys,'argv',['run_stock_launcher.py','--debug','--finish-setup','--switch-file',str(switch)]),patch.object(runner.subprocess,'run',return_value=SimpleNamespace(returncode=128)) as stop,patch.object(runner.subprocess,'Popen',return_value=SimpleNamespace(pid=123)) as launch,contextlib.redirect_stdout(io.StringIO()):
                runner.main()
            self.assertEqual([call.args[0] for call in stop.call_args_list],[[str(wine),'taskkill','/F','/IM','winedbg.exe'],[str(wine),'taskkill','/F','/IM','Inn.games.exe'],[str(wine),'taskkill','/F','/IM','Launcher.exe'],[str(wine),'taskkill','/F','/IM','explorer.exe']])
            self.assertIn('/d',launch.call_args.args[0])
            self.assertEqual(launch.call_args.args[0][-2:],['/sw',r'C:\lineage-relay\cef-switches.txt'])
            self.assertEqual((prefix/'drive_c/lineage-relay/cef-switches.txt').read_text(),'disable-gpu\n')
            self.assertEqual(stop.call_args.kwargs['env']['WINEPREFIX'],str(prefix.resolve()))
    def test_data_and_helpers_follow_relocated_environment(self):
        with tempfile.TemporaryDirectory(prefix='lineage bundle ') as folder:
            data=Path(folder)/'Private Data';resources=Path(folder)/'Moved.app/Contents/Resources'
            env=os.environ.copy();env.update(LINEAGE_DATA_DIR=str(data),LINEAGE_RESOURCES_DIR=str(resources),LINEAGE_PACKAGED='1')
            result=subprocess.check_output([sys.executable,'-c','import app_paths,json; print(json.dumps([str(app_paths.CONFIG),str(app_paths.HELPERS)]))'],cwd=ROOT,env=env,text=True)
            self.assertEqual(json.loads(result),[str(data.resolve()/'config.local.json'),str(resources.resolve()/'Payload/helpers')])
            self.assertFalse(data.exists())
    def test_source_release_lists_all_standalone_sources(self):
        spec=importlib.util.spec_from_file_location('package_source',ROOT/'package_source.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        for name in ['AppPaths.swift','app_paths.py','install_bundle.py','build_bundle.py','extract_python_licenses.py','test_bundle.py']:
            self.assertIn(name,m.FILES)
        self.assertFalse(any(name.startswith(('.local/','dist/','.build/')) for name in m.FILES))
    @unittest.skipUnless(os.environ.get('LINEAGE_TEST_APP'), 'Set LINEAGE_TEST_APP to exercise an installed app')
    def test_window_helper_does_not_request_a_console(self):
        app=Path(os.environ['LINEAGE_TEST_APP'])
        data=(app/'Contents/Resources/Payload/helpers/NativeLauncherWindow.exe').read_bytes()
        pe=struct.unpack_from('<I',data,0x3c)[0]
        self.assertEqual(data[pe:pe+4],b'PE\0\0')
        self.assertEqual(struct.unpack_from('<H',data,pe+24+68)[0],2)
    @unittest.skipUnless(os.environ.get('LINEAGE_TEST_APP'), 'Set LINEAGE_TEST_APP to exercise an installed app')
    def test_embedded_python_leaves_signature_intact(self):
        app=Path(os.environ['LINEAGE_TEST_APP'])
        python=app/'Contents/Resources/Python/bin/python3'
        env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env.pop('PYTHONHOME',None);env.pop('PYTHONPATH',None)
        subprocess.run([str(python),'-B','-c','import ssl,json,tarfile,zipfile,subprocess; print("Embedded standard library OK")'],env=env,cwd='/private/tmp',check=True)
        subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
    def test_packaged_installer_does_not_invoke_build_tools(self):
        import ast
        tree=ast.parse((ROOT/'install_bundle.py').read_text())
        strings=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str)]
        self.assertFalse(any(s in {'xcrun','make','swiftc','clang','otool','/usr/bin/python3'} for s in strings))

if __name__=='__main__':unittest.main()
