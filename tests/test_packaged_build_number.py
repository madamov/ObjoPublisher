"""Run with: python3 -m unittest discover -s tests -v"""
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'


def checker(platform):
    text = (WORKFLOWS / f'publish_objo_{platform}.yml').read_text()
    step = text.split('      - name: Verify packaged build number\n', 1)[1].split('      - name:', 1)[0]
    assert "if: inputs.build-number != ''" in step
    script = step.split(" - <<'PYTHON'\n", 1)[1].split('          PYTHON\n', 1)[0]
    return '\n'.join(line[10:] for line in script.splitlines()) + '\n'


class PackagedBuildNumberTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='objo-check-test-')
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.artifacts = self.output / 'artifacts'
        self.artifacts.mkdir()
        self.environment = dict(os.environ, OUTPUT_DIRECTORY=str(self.output), BUILD_NUMBER='13')

    def archive(self, extension, entries):
        path = self.artifacts / ('app.' + extension)
        if extension in ('zip', 'msix'):
            with zipfile.ZipFile(path, 'w') as archive:
                for name, value in entries:
                    archive.writestr(name, value)
        else:
            with tarfile.open(path, 'w:gz') as archive:
                for name, value in entries:
                    entry = tarfile.TarInfo(name)
                    entry.size = len(value)
                    archive.addfile(entry, io.BytesIO(value))
        return path

    def execute(self, platform):
        return subprocess.run(['python3', '-c', checker(platform)], env=self.environment,
                              capture_output=True, text=True)

    def test_archive_cases(self):
        resource = 'app/Resources/Files/BUILD_NUMBER.txt'
        cases = [
            ('valid', [(resource, b'13\n')], True),
            ('missing', [('app/README.txt', b'13\n')], False),
            ('misplaced', [('app/BUILD_NUMBER.txt', b'13\n')], False),
            ('wrong', [(resource, b'12\n')], False),
            ('missing newline', [(resource, b'13')], False),
            ('extra data', [(resource, b'13\nextra')], False),
            ('one invalid copy', [(resource, b'13\n'), ('helper/Resources/Files/BUILD_NUMBER.txt', b'12\n')], False),
        ]
        for platform in ('linux', 'windows', 'windows_objosign'):
            for extension in ('zip', 'msix', 'tar.gz', 'tgz'):
                for name, entries, valid in cases:
                    with self.subTest(platform=platform, extension=extension, case=name):
                        path = self.archive(extension, entries)
                        result = self.execute(platform)
                        self.assertEqual(result.returncode == 0, valid, result.stdout + result.stderr)
                        path.unlink()

    def test_empty_and_corrupt_artifacts_fail(self):
        for platform in ('linux', 'windows', 'windows_objosign'):
            with self.subTest(platform=platform):
                self.assertNotEqual(self.execute(platform).returncode, 0)
                path = self.artifacts / 'broken.zip'
                path.write_bytes(b'not a ZIP file')
                self.assertNotEqual(self.execute(platform).returncode, 0)
                path.unlink()

    def test_every_archive_is_checked(self):
        for platform in ('linux', 'windows', 'windows_objosign'):
            with self.subTest(platform=platform):
                good = self.archive('zip', [('app/Resources/Files/BUILD_NUMBER.txt', b'13\n')])
                bad = self.archive('tgz', [('app/Resources/Files/BUILD_NUMBER.txt', b'12\n')])
                self.assertNotEqual(self.execute(platform).returncode, 0)
                good.unlink()
                bad.unlink()

    def test_macos_mount_cleanup_and_resource_cases(self):
        # Simulate mounting so these failure/cleanup tests can run on any OS.
        dmg = self.artifacts / 'app.dmg'
        dmg.touch()
        cases = [('valid', b'13\n', True), ('wrong', b'12\n', False),
                 ('missing', None, False), ('no app', None, False)]
        for name, value, valid in cases:
            calls = []
            def hdiutil(arguments, **kwargs):
                calls.append(arguments)
                if arguments[1] == 'attach' and name != 'no app':
                    resource = Path(arguments[-1]) / 'App.app/Contents/Resources/Resources/Files/BUILD_NUMBER.txt'
                    resource.parent.mkdir(parents=True)
                    if value is not None:
                        resource.write_bytes(value)
                return subprocess.CompletedProcess(arguments, 0)
            with self.subTest(case=name), patch.dict(os.environ, self.environment), patch('subprocess.run', side_effect=hdiutil), patch('builtins.print'):
                if valid:
                    exec(compile(checker('macos'), '<macos checker>', 'exec'), {})
                else:
                    with self.assertRaises(SystemExit):
                        exec(compile(checker('macos'), '<macos checker>', 'exec'), {})
                self.assertEqual(calls[0][1], 'attach')
                self.assertIn('-readonly', calls[0])
                self.assertEqual(calls[-1][1], 'detach')
                self.assertEqual(calls[0][-1], calls[-1][-1])
                self.assertFalse(Path(calls[-1][-1]).exists())


if __name__ == '__main__':
    unittest.main()
