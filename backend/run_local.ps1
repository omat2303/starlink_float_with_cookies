# StarPanel en local: levanta el backend (uvicorn) y el panel (Next) en ventanas
# separadas. Cierra las ventanas para detener cada servicio.
$backend = $PSScriptRoot
$frontend = Join-Path (Split-Path $backend -Parent) 'frontend'

Start-Process (Join-Path $backend 'venv\Scripts\python.exe') `
  -ArgumentList '-m', 'uvicorn', 'main:app', '--port', '8000' `
  -WorkingDirectory $backend

Start-Process 'npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory $frontend

Start-Sleep -Seconds 6
Start-Process 'http://localhost:3000'
