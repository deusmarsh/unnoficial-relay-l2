"""Provide the physical font files used by the game's native UI, inside its prefix."""
from pathlib import Path
import shutil
import sys

SYSTEM_FONTS = Path('/System/Library/Fonts/Supplemental')
FONT_FILES = (('Arial.ttf', 'Arial.ttf'), ('Tahoma.ttf', 'tahoma.ttf'))


def prepare_game_fonts(prefix, source_dir=SYSTEM_FONTS):
    """Copy only absent fonts from this Mac; preserve existing files and casing.

    Wine's name-based GDI font lookup is insufficient: the game opens these
    Windows font paths directly. No fonts are downloaded or distributed here.
    """
    prefix = Path(prefix).resolve()
    if not (prefix / 'drive_c').is_dir():
        raise RuntimeError('Initialize the configured Wine prefix before preparing game fonts.')
    fonts = prefix / 'drive_c/windows/Fonts'
    try:
        fonts.resolve().relative_to(prefix)
    except ValueError:
        raise RuntimeError('The Windows Fonts directory must stay inside the configured prefix.') from None
    fonts.mkdir(parents=True, exist_ok=True)
    existing = {item.name.casefold(): item for item in fonts.iterdir()}
    result = {'installed': [], 'preserved': [], 'missing': []}
    for source_name, target_name in FONT_FILES:
        current = existing.get(target_name.casefold())
        if current is not None:
            if not current.is_file():
                raise RuntimeError('The game font path is not a readable file: ' + target_name)
            result['preserved'].append(current.name)
            continue
        source = Path(source_dir) / source_name
        if not source.is_file():
            result['missing'].append(source_name)
            continue
        destination = fonts / target_name
        with source.open('rb') as incoming, destination.open('xb') as outgoing:
            try:
                shutil.copyfileobj(incoming, outgoing)
            except BaseException:
                destination.unlink()
                raise
        result['installed'].append(target_name)
    if result['missing']:
        print('Game UI text may be missing: these local macOS supplemental fonts '
              'are unavailable: ' + ', '.join(result['missing']) +
              '. See INSTALL.md, Game UI fonts.', file=sys.stderr)
    return result
