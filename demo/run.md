# Run Dubai-io

Two ways. Option A needs nothing. Option B gives you the real AI (Luna) on your PC and phone.

## A. Just look (no install)

Open a link on your phone or PC:
- Cyan: https://claude.ai/artifact/YZgGtUTmXuarcz97FvGH1w
- Chromatic: https://claude.ai/artifact/DukxEKh196BPzRaREFuKqe

Chat uses the built-in keyword router here; the links can't reach your PC.

## B. Run on your PC with real Luna (PowerShell)

### First time only

```powershell
cd G:\Haitham\VsCode\contest\apps\api
python -m venv .venv
$env:REQUESTS_CA_BUNDLE = ""          # this PC points it at a deleted file; clears it for this window
.\.venv\Scripts\python -m pip install -r requirements.txt
```

Keys go in `demo\.env` (already there, never committed):

```
OPENAI_API_KEY=...
GOOGLE_PLACES_KEY=...
```

Optional, also in `demo\.env`: `LUNA_MODEL=gpt-6.1-sol` and `LUNA_EFFORT=medium` (faster). The default is `gpt-6-luna` with `high`.

### Every time

```powershell
cd G:\Haitham\VsCode\contest\apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- PC: http://localhost:8000 (opens the cyan lab; the chromatic one is at `/lab/home-v2-chromatic.html`)
- iPhone (same Wi-Fi): `http://<your PC IP>:8000`. Find the IP with `ipconfig` → IPv4. Allow the Windows firewall prompt.
- Check it's alive: http://localhost:8000/api/health (shows the model, and whether both keys are set).

Stop with `Ctrl+C`.

## Restart the demo from the start

Tap the **Dubai-io** logo, or Me → "Replay landing and Wi-Fi sign-in", or add `#wifi` to the address.

## Tests

```powershell
node G:\Haitham\VsCode\contest\demo\lab\tests\profile.test.mjs           # profile math, 92 checks
cd G:\Haitham\VsCode\contest\apps\api
.\.venv\Scripts\python -m pytest -q                                       # offline Luna checks
$env:RUN_LIVE = "1"; .\.venv\Scripts\python -m pytest -q -k golden        # 11 live model calls (costs a little)
```

## Old v1 demo

```powershell
cd G:\Haitham\VsCode\contest\demo
python -m http.server 8765
```

Then open http://localhost:8765.
