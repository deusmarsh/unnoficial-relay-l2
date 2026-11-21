"""Launch only the configured runtime; discard inherited renderer experiments."""
import os
from pathlib import Path

METAL_PROFILE = 'metal-no-audio-v1'


def wine_environment(config):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('WINE', 'DYLD_', 'DXVK', 'MVK_', 'VK_',
                                  'MTLD3D', 'MTL_', 'FEX_', 'ROSETTA_', 'X87_', 'COMPlus_', 'DOTNET_'))}
    env.update(WINEPREFIX=str(Path(config['prefix']).expanduser().resolve()),
               WINEDEBUG='-all,err+all', DOTNET_MULTILEVEL_LOOKUP='0',
               WINEDLLOVERRIDES='winemenubuilder.exe=d;winedbg.exe=d',
               DYLD_FALLBACK_LIBRARY_PATH=':'.join(str(Path(p).expanduser().resolve())
                                                  for p in config['library_paths']) + ':/usr/local/lib:/usr/lib')
    profile = config.get('runtime_profile')
    if config.get('material_fix') is not None:
        from material_fix import verify_renderer
        verify_renderer(config)
    if profile == METAL_PROFILE:
        if config.get('x87_audio') is not None:
            from x87_audio import verified_sidecar
            env['ROSETTA_X87_PATH'] = str(verified_sidecar(config))
        else:
            env['WINEDLLOVERRIDES'] += ';winecoreaudio.drv=d'
        env['DYLD_FRAMEWORK_PATH'] = str(Path(config['framework_path']).expanduser().resolve())
        env['MTLD3D_CONFIG'] = 'color.hdr.enable=false;shader.asyncCompile=false'
    elif profile is not None:
        raise RuntimeError('Unknown runtime profile. Run ./dev setup in a new directory.')
    elif config.get('x87_audio') is not None:
        raise RuntimeError('x87 audio requires the configured Metal source runtime.')
    return env
