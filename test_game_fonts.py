"""Font path regression checks; no Wine, real fonts or game session required."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from prepare_game_fonts import prepare_game_fonts


class GameFontChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.prefix = self.root / 'prefix'
        (self.prefix / 'drive_c').mkdir(parents=True)
        self.source = self.root / 'system-fonts'
        self.source.mkdir()
        for name in ('Arial.ttf', 'Tahoma.ttf'):
            (self.source / name).write_bytes(('test font ' + name).encode())
        self.fonts = self.prefix / 'drive_c/windows/Fonts'

    def test_direct_windows_paths_exist_and_second_run_changes_nothing(self):
        result = prepare_game_fonts(self.prefix, self.source)
        self.assertEqual(result['installed'], ['Arial.ttf', 'tahoma.ttf'])
        for source, target in [('Arial.ttf', 'Arial.ttf'), ('Tahoma.ttf', 'tahoma.ttf')]:
            self.assertEqual((self.fonts / target).read_bytes(), (self.source / source).read_bytes())
        before = {p.name: p.stat().st_mtime_ns for p in self.fonts.iterdir()}
        result = prepare_game_fonts(self.prefix, self.source)
        self.assertEqual(result['installed'], [])
        self.assertEqual(before, {p.name: p.stat().st_mtime_ns for p in self.fonts.iterdir()})

    def test_existing_fonts_with_different_casing_are_preserved(self):
        self.fonts.mkdir(parents=True)
        (self.fonts / 'TAHOMA.TTF').write_bytes(b'existing user font')
        prepare_game_fonts(self.prefix, self.source)
        self.assertEqual((self.fonts / 'TAHOMA.TTF').read_bytes(), b'existing user font')
        self.assertEqual(len(list(self.fonts.iterdir())), 2)

    def test_missing_local_source_is_reported_without_downloading(self):
        (self.source / 'Tahoma.ttf').unlink()
        with contextlib.redirect_stderr(io.StringIO()) as warning:
            result = prepare_game_fonts(self.prefix, self.source)
        self.assertEqual(result['missing'], ['Tahoma.ttf'])
        self.assertIn('Tahoma.ttf', warning.getvalue())
        self.assertFalse((self.fonts / 'tahoma.ttf').exists())

    def test_fonts_directory_cannot_redirect_writes_outside_prefix(self):
        outside = self.root / 'outside'
        outside.mkdir()
        self.fonts.parent.mkdir()
        self.fonts.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(RuntimeError, 'inside the configured prefix'):
            prepare_game_fonts(self.prefix, self.source)
        self.assertEqual(list(outside.iterdir()), [])

    def test_typo_does_not_create_another_prefix(self):
        absent = self.root / 'absent'
        with self.assertRaisesRegex(RuntimeError, 'Initialize'):
            prepare_game_fonts(absent, self.source)
        self.assertFalse(absent.exists())


if __name__ == '__main__':
    unittest.main()
