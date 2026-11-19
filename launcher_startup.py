"""Bounded startup recovery; never stream frames or reload an active launcher page."""
import json
import time
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

from launcher_connection import LocalWebSocket


def finish_loading():
    """Reload a stuck splash at most once, after the official bridge is available."""
    opener = build_opener(ProxyHandler({}))
    start = time.monotonic()
    reloaded = False
    bound_since = None
    while time.monotonic() - start < 90:
        try:
            with opener.open('http://127.0.0.1:8088/json/list', timeout=2) as response:
                pages = json.load(response)
            pages = [p for p in pages if p.get('type') == 'page' and
                     urlsplit(p.get('url', '')).hostname == 'launcher.eu.4game.com' and
                     not urlsplit(p.get('url', '')).path.startswith('/window/')]
            if len(pages) != 1:
                time.sleep(2)
                continue
            ws = LocalWebSocket(pages[0]['webSocketDebuggerUrl'])
            ws.socket.settimeout(3)
            try:
                result = ws.call('Runtime.evaluate', {'expression':
                    'JSON.stringify({path:location.pathname,state:document.readyState,bridge:typeof LAUNCHER})',
                    'returnByValue': True})
                state = json.loads(result['result']['value'])
                if state['path'] != '/splash' and state['state'] == 'complete' and state['bridge'] == 'object':
                    print('Official launcher page and native connection are ready.', flush=True)
                    return True
                if state['path'] == '/splash' and state['state'] == 'complete' and state['bridge'] == 'object':
                    bound_since = bound_since or time.monotonic()
                    if not reloaded and time.monotonic() - start > 25 and time.monotonic() - bound_since > 8:
                        ws.call('Page.reload', {'ignoreCache': False})
                        reloaded = True
                        print('Reloaded the startup splash after its native connection became ready.', flush=True)
                else:
                    bound_since = None
            finally:
                ws.close()
        except (OSError, ValueError, KeyError, RuntimeError, ConnectionError):
            pass
        time.sleep(2)
    print('Launcher is still loading. Its window remains open; no further reloads were sent.', flush=True)
    return False
