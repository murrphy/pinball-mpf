"""Exercise the installed MPF launcher and cabinet wrapper without audio hardware."""
import configparser
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mpf.commands.both import _spawn_gmc

ROOT = Path(__file__).resolve().parents[1]


class GmcLauncherTest(unittest.TestCase):
    def test_configured_wrapper_is_executable_and_preserves_real_audio_arguments(self):
        config = configparser.ConfigParser(strict=False)
        config.read(ROOT / 'gmc.cfg')
        wrapper = config.get('cli', 'godot_exec_path').strip('"')
        self.assertTrue(os.access(ROOT / wrapper, os.X_OK))
        with tempfile.TemporaryDirectory() as directory:
            fake = Path(directory) / 'godot'
            output = Path(directory) / 'args.json'
            fake.write_text(f'#!{sys.executable}\n'
                            'import json,os,sys\n'
                            'open(os.environ["ARG_CAPTURE"],"w").write(json.dumps(sys.argv[1:]))\n')
            fake.chmod(0o755)
            env = dict(os.environ, GODOT_BIN=str(fake), ARG_CAPTURE=str(output))
            env.pop('DISPLAY', None)
            env.pop('WAYLAND_DISPLAY', None)
            subprocess.run([wrapper, '-v', '--script', 'res://gmc_tests/test_headless_runtime.gd'],
                           cwd=ROOT, env=env, check=True)
            self.assertEqual(['--display-driver', 'headless', '--audio-driver', 'PulseAudio',
                              '-v', '--script', 'res://gmc_tests/test_headless_runtime.gd'],
                             json.loads(output.read_text()))

    def test_installed_mpf_both_spawns_configured_executable_in_project(self):
        args = SimpleNamespace(godot_exec_path=str(ROOT / 'tools/godot-cabinet'),
                               gmc_project_path=str(ROOT))
        with patch('mpf.commands.both.subprocess.Popen') as spawn:
            _spawn_gmc(args, ['-a'])
        spawn.assert_called_once_with([str(ROOT / 'tools/godot-cabinet')], cwd=str(ROOT))
