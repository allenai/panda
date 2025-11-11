@echo off
rem === Launch Panda MCP server with correct module path ===
setlocal
set PYTHONPATH=C:\Users\peter\Dropbox\Desktop\2025\Panda\panda
rem === below: disable buffering (so all output is written immediately) ===
set PYTHONUNBUFFERED=1
"C:\Users\peter\anaconda3\envs\panda\python.exe" -u -m panda.mcp_server 2> C:\Users\peter\Dropbox\Desktop\2025\Panda\panda\run_panda.log
endlocal


