# First Python API

A local FastAPI process on your laptop. It is **not** talking to the NVIDIA
Air fabric, Prometheus, or the switches. When this works, you have proven
you can start an HTTP service, hit it, and read the JSON it returns.

## What you are running

```
your browser / curl  →  HTTP  →  uvicorn  →  FastAPI (main.py)  →  JSON back
```

- **FastAPI** is the app: it maps a URL path to a Python function.
- **uvicorn** is the server: it listens on a TCP port and hands HTTP
  requests to FastAPI.

That split is the same idea as "BGP daemon vs the box that runs it." The
app defines behavior; the process listens on a port.

## One-time setup (PowerShell)

From the repo root:

```powershell
cd API
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` is blocked, run this once in that same PowerShell window,
then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Start it

Stay in `API` with the venv active:

```powershell
uvicorn main:app --reload
```

`--reload` restarts the process when you save `main.py`. Leave this window
running. Open a second terminal for tests.

You should see something like:

```
Uvicorn running on http://127.0.0.1:8000
```

`127.0.0.1` means "this machine only." Nothing on the fabric can reach it.

## Hit it (checkpoint)

Browser: open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) then
[http://127.0.0.1:8000/health](http://127.0.0.1:8000/health).

Or from a second PowerShell window (venv not required for curl):

```powershell
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

Expected:

- `/` → `{"message":"API is up","try_next":["/health","/docs"]}`
- `/health` → `{"status":"ok"}`

Interactive docs (generated from the Python functions):
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Stop the server with `Ctrl+C` in the uvicorn window.

## How to read `main.py`

1. `app = FastAPI(...)` creates the application object uvicorn loads
   (`main:app` means "file `main.py`, variable `app`").
2. `@app.get("/health")` is a **decorator**: "when an HTTP GET hits this
   path, run the function below."
3. The function **return value** is serialized to JSON. Status code is 200
   unless you raise an error.

That is a route. A real fabric API is the same pattern with more routes
and real data behind them.

## Not claimed

This folder does not scrape NVUE, gNMI, or Prometheus. No auth. No
TLS. No listen on a fabric mgmt IP.
