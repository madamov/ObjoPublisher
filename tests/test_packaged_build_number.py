"""Run with: python3 -m unittest discover -s tests -v"""
import io
import json
import datetime
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

METADATA = {'version': '1.0.1', 'build_number': 13, 'built_at': '2026-10-23T09:06:57Z'}
VALID = (json.dumps(METADATA, indent=2) + '\n').encode()
WRONG = (json.dumps(dict(METADATA, build_number=12), indent=2) + '\n').encode()


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
        expected = self.output / 'expected.json'
        expected.write_bytes(VALID)
        self.environment = dict(os.environ, OUTPUT_DIRECTORY=str(self.output), BUILD_NUMBER='13', BUILD_METADATA_PATH=str(expected))

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
        resource = 'app/Resources/Files/BUILD_NUMBER.json'
        cases = [
            ('valid', [(resource, VALID)], True),
            ('missing', [('app/README.txt', VALID)], False),
            ('misplaced', [('app/BUILD_NUMBER.json', VALID)], False),
            ('wrong', [(resource, WRONG)], False),
            ('malformed JSON', [(resource, b'{invalid')], False),
            ('wrong version', [(resource, json.dumps(dict(METADATA, version='9.0.0')).encode())], False),
            ('wrong timestamp', [(resource, json.dumps(dict(METADATA, built_at='2026-01-01T00:00:00Z')).encode())], False),
            ('extra data', [(resource, b'13\nextra')], False),
            ('one invalid copy', [(resource, VALID), ('helper/Resources/Files/BUILD_NUMBER.json', WRONG)], False),
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
                good = self.archive('zip', [('app/Resources/Files/BUILD_NUMBER.json', VALID)])
                bad = self.archive('tgz', [('app/Resources/Files/BUILD_NUMBER.json', WRONG)])
                self.assertNotEqual(self.execute(platform).returncode, 0)
                good.unlink()
                bad.unlink()

    def test_metadata_generation(self):
        for platform in ('macos', 'linux', 'windows', 'windows_objosign'):
            text = (WORKFLOWS / f'publish_objo_{platform}.yml').read_text()
            self.assertLess(text.index('      - name: Configure application version'), text.index('      - name: Bundle build number'))
            step = text.split('      - name: Bundle build number as an application resource\n', 1)[1].split('      - name:', 1)[0]
            script = step.split(" - <<'PYTHON'\n", 1)[1].split('          PYTHON\n', 1)[0]
            script = '\n'.join(line[10:] for line in script.splitlines()) + '\n'
            for version, settings, expected_version in [
                ('2.3.4-beta.1+ci', {'BuildSettings': {'MajorVersion': 1}}, '2.3.4-beta.1+ci'),
                ('', {'BuildSettings': {'MajorVersion': 2, 'MinorVersion': 3, 'PatchVersion': 4}}, '2.3.4'),
                ('invalid', {'MajorVersion': 3, 'MinorVersion': 2, 'PatchVersion': 1}, '3.2.1'),
            ]:
                with self.subTest(platform=platform, version=version):
                    project = self.output / 'Project with spaces' / 'project.json'
                    project.parent.mkdir(exist_ok=True)
                    project.write_text(json.dumps(settings))
                    resources = project.parent / 'Resources/Files'
                    resources.mkdir(parents=True, exist_ok=True)
                    legacy = resources / 'BUILD_NUMBER.txt'
                    legacy.write_text('12\n')
                    env = dict(self.environment, PROJECT_FILE=str(project), APP_VERSION=version,
                               RUNNER_TEMP=str(self.output), GITHUB_ENV=str(self.output / 'env'))
                    result = subprocess.run(['python3', '-c', script], env=env, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    generated = resources / 'BUILD_NUMBER.json'
                    metadata = json.loads(generated.read_bytes())
                    self.assertEqual(metadata['version'], expected_version)
                    self.assertEqual(metadata['build_number'], 13)
                    stamp = datetime.datetime.strptime(metadata['built_at'], '%Y-%m-%dT%H:%M:%SZ')
                    self.assertLess(abs((datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) - stamp).total_seconds()), 30)
                    self.assertEqual(generated.read_bytes(), (self.output / 'objo-build-metadata.json').read_bytes())
                    self.assertFalse(legacy.exists())
                    self.assertIn('BUILD_METADATA_PATH=', (self.output / 'env').read_text())
                    for number in ('-1', '01', '1.2', 'abc', ''):
                        result = subprocess.run(['python3', '-c', script], env=dict(env, BUILD_NUMBER=number), capture_output=True, text=True)
                        self.assertNotEqual(result.returncode, 0)

    def test_macos_mount_cleanup_and_resource_cases(self):
        # Simulate mounting so these failure/cleanup tests can run on any OS.
        dmg = self.artifacts / 'app.dmg'
        dmg.touch()
        cases = [('valid', VALID, True), ('wrong', WRONG, False),
                 ('missing', None, False), ('no app', None, False)]
        for name, value, valid in cases:
            calls = []
            def hdiutil(arguments, **kwargs):
                calls.append(arguments)
                if arguments[1] == 'attach' and name != 'no app':
                    resource = Path(arguments[-1]) / 'App.app/Contents/Resources/Resources/Files/BUILD_NUMBER.json'
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
