"""Screenshots of the running app for design reviews: headless Edge driven over the DevTools protocol (Streamlit draws
over a websocket, so a plain --screenshot fires before anything renders).

    .venv\\Scripts\\python tools\\screenshot.py http://localhost:8521/?theme=spire renderings/spire 0 900 1700
writes renderings/spire-1.png, -2.png, ... at a 1440x900 viewport, scrolled to each offset given (px).
"""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from websockets.asyncio.client import connect  # websockets ships with Streamlit

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9333
SCROLLER = ("[...document.querySelectorAll('*')].find(e => e.scrollHeight > e.clientHeight + 40 && "
            "['auto','scroll'].includes(getComputedStyle(e).overflowY) && e.clientWidth > 600)")


async def shoot(url: str, prefix: str, offsets: list[int], width: int = 1440, height: int = 900, wait: int = 16):
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={PORT}", "--hide-scrollbars",
                             f"--user-data-dir={tempfile.mkdtemp()}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                tabs = httpx.get(f"http://127.0.0.1:{PORT}/json/list").json()
                break
            except httpx.HTTPError:
                time.sleep(0.25)
        ws = await connect(next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page"), max_size=None)
        seq = 0

        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal seq
            seq += 1
            await ws.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == seq:
                    return msg.get("result", {})

        await call("Emulation.setDeviceMetricsOverride",
                   {"width": width, "height": height, "deviceScaleFactor": 1, "mobile": False})
        await call("Page.navigate", {"url": url})
        await asyncio.sleep(wait)
        for i, y in enumerate(offsets, 1):
            await call("Runtime.evaluate", {"expression": f"(() => {{ const s = {SCROLLER}; if (s) s.scrollTo(0, {y}); "
                                                          f"else window.scrollTo(0, {y}); }})()"})
            await asyncio.sleep(1.5)
            img = await call("Page.captureScreenshot", {"format": "png"})
            out = Path(f"{prefix}-{i}.png")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(base64.b64decode(img["data"]))
            print(out)
        await ws.close()
    finally:
        proc.terminate()


if __name__ == "__main__":
    asyncio.run(shoot(sys.argv[1], sys.argv[2], [int(x) for x in sys.argv[3:]] or [0]))
