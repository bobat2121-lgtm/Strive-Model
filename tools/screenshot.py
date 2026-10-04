"""Screenshots of the running app for design reviews: headless Edge driven over the DevTools protocol (Streamlit draws
over a websocket, so a plain --screenshot fires before anything renders).

    .venv\\Scripts\\python tools\\screenshot.py http://localhost:8521/?theme=vault renderings/vault 0 760 1500
writes renderings/vault-1.png, -2.png, ... at a 1440x900 viewport, scrolled to each offset given (px).

    .venv\\Scripts\\python tools\\screenshot.py http://localhost:8521/ renderings/vault.gif 12
records 12 seconds at the top of the page as an animated GIF (to show motion).
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


async def shoot(url: str, prefix: str, offsets: list[int], width: int = 1440, height: int = 900, wait: int = 16,
                record: float = 0.0, fps: int = 6, scale: float = 0.6):
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
        if record:
            from io import BytesIO
            from PIL import Image
            frames, t_end = [], time.time() + record
            while time.time() < t_end:
                t0 = time.time()
                img = await call("Page.captureScreenshot", {"format": "jpeg", "quality": 85})
                im = Image.open(BytesIO(base64.b64decode(img["data"]))).convert("RGB")
                frames.append(im.resize((int(width * scale), int(height * scale)), Image.LANCZOS))
                await asyncio.sleep(max(0.0, 1 / fps - (time.time() - t0)))
            frames[0].save(prefix, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0,
                           optimize=True)
            print(prefix, f"({len(frames)} frames)")
            offsets = []
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
    url, out, rest = sys.argv[1], sys.argv[2], sys.argv[3:]
    if out.endswith(".gif"):
        asyncio.run(shoot(url, out, [], record=float(rest[0]) if rest else 10.0))
    else:
        asyncio.run(shoot(url, out, [int(x) for x in rest] or [0]))
