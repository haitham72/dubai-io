# Run the demo

Static HTML/JS, no build, no `npm`. Needs Python 3 only.

## First time

```powershell
python --version
```

Prints a version? You're set. If not, install Python 3 from python.org and tick "Add to PATH".

## Every time

```powershell
cd G:\Haitham\VsCode\contest\demo
Start-Process http://localhost:8765
python -m http.server 8765
```

Page blank or "can't connect"? Refresh once, the server was a second behind the browser.

Keep that terminal open while you use the demo. Stop with `Ctrl+C`.

## Port already in use

```powershell
python -m http.server 8766
```

Then open http://localhost:8766.
