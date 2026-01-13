"""
See mcp.json for example MCP declaration

This file declares three MCP tools that hook into Panda:

   # set Panda going on task, putting the results in CURSOR_EXPT_FOLFER. Returns the JobId immediately
   def start_research(task: str, folder:str=CURSOR_EXPT_FOLDER) -> dict

   # poll to see if JobId research is done. 
   # If still running, returns: {"status": "running",   "job_id": "<the given job_id>"}
   # if completed, returns:     {"status": "completed", "job_id": "<the given job_id>", "summary": "<the short text summary of the result>"}
   def get_research_status(job_id: str) -> dict

   # This function waits (blocks) until the research is complete, returning the completed status (above) when finished.
   def wait_research(job_id: str, poll_interval_s: int = 2, timeout_s: int = 1800) -> dict

----------

Top-level call to Panda:
  run_panda(task, background_knowledge=None, force_report=True, outputs_dir="output_iterpanda")            
  Cursor usage:
  Call start_research with task='What is 1 + 1?'
  Call start_research with task='What is 1 + 1?' and folder='reports/2025-10-07'
  Call get_research_status with job_id='

Debug test for my mcp_server:
C:\\Users\\peter\\anaconda3\\envs\\panda\\python.exe C:\\Users\\peter\\Dropbox\\Desktop\\2025\\Panda\\panda\\panda\\mcp_server.py
"""

from mcp.server.fastmcp import FastMCP
import time, uuid, threading
from mcp.types import Resource
import os
import sys
import logging

import panda

CURSOR_EXPT_FOLDER = "output_iterpanda"
LOG_PATH = "C:/Users/peter/Dropbox/Desktop/2025/Panda/panda/run_panda.log"

mcp = FastMCP("panda")

# Toy test case
#@mcp.tool()
#def ping() -> str:
#    """Simple health check."""
#    return "pong"
#
# NOTE: print to stderr with MCP
#print("DEBUG: registering tools...", file=sys.stderr, flush=True)

_jobs = {}  # job_id -> {"status": "...", "result": {...} or None, "error": str|None}

"""
Safe version below to capture ALL stdout output. Note LiteLLM still produces stdout messages on error:
Give Feedback / Get Help: https://github.com/BerriAI/litellm/issues/new
LiteLLM.Info: If you need to debug this error, use `litellm._turn_on_debug()'.

GPT says: 
  "By default, modules like LiteLLM may produce their own 'info' prints (not via the standard 
   Python logging or your logger settings). You'll need to suppress or redirect those explicitly in your code or configuration."
"""
import contextlib, io
import os

def _worker(job_id, task, folder=CURSOR_EXPT_FOLDER):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = panda.run_panda(task=task, force_report=True, outputs_dir=folder)
        _jobs[job_id] = {"status": "done", "result": result, "error": None}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}

@mcp.tool()
def start_research(task: str, folder:str=CURSOR_EXPT_FOLDER) -> dict:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    threading.Thread(target=_worker, args=(job_id, task, folder), daemon=True).start()
    return {"job_id": job_id, "status": "running"}

# ======================================================================

def _worker2(job_id, workspace_folder):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = panda.run_cursor_panda(workspace_folder=workspace_folder)
        _jobs[job_id] = {"status": "done", "result": result, "error": None}
    except Exception as e:
        _jobs[job_id] = {"status": "error", "result": None, "error": str(e)}

# Cursor panda
@mcp.tool()
def start_auto_research() -> dict:
    job_id = str(uuid.uuid4())
    workspace_folder = os.getenv("WORKSPACE_FOLDER")
    if workspace_folder is None:
        logger.warning(f"Yikes! Environment variable WORKSPACE_FOLDER not defined, please define it! Assuming Panda root dir ({agent_config.ROOT_DIR}) for now....")
        workspace_folder = panda.panda_agent.config.ROOT_DIR
    _jobs[job_id] = {"status": "running", "result": None, "error": None}
    threading.Thread(target=_worker2, args=(job_id,workspace_folder), daemon=True).start()
    return {"job_id": job_id, "status": "running"}

# ======================================================================

@mcp.tool()
def get_research_status(job_id: str) -> dict:
    try:
        j = _jobs.get(job_id)
        if not j:
            return {"status": "not_found", "job_id": job_id}

        payload = {
            "status": j.get("status"),
            "job_id": job_id,
        }

        # Include error if there was one
        if j.get("error"):
            payload["error"] = j["error"]

        # Include summary if it exists
        if j.get("result") and isinstance(j["result"], dict):
            payload["summary"] = j["result"].get("summary")

        return payload

    except Exception as e:
        import traceback, sys
        print(f"[ERROR] get_research_status crashed:\n{traceback.format_exc()}", file=sys.stderr)
        return {"status": "error", "job_id": job_id, "error": str(e)}

# ======================================================================

# wait_research (deliberatly) blocks inside the tool call, so Cursor will show a spinner and wait until the function returns (either done/error or timeout).
@mcp.tool()
def wait_research(job_id: str, poll_interval_s: int = 2, timeout_s: int = 1800) -> dict:
    """Poll until the job finishes or times out."""
    start = time.time()
    while time.time() - start < timeout_s:
        st = get_research_status(job_id)
        # Optional: progress reporting if your SDK/client supports it:
        # mcp.report_progress(f"Status: {st.get('status','?')}")
        if st.get("status") == "done" or st.get("status") == "error":
            return st
        time.sleep(poll_interval_s)
    return {"status": "timeout", "job_id": job_id}

### ======================================================================
###    Not sure how useful this is....
### Access in Agent window by "Open the panda-log resource"
### ======================================================================    

@mcp.resource("panda://run_panda.log")
def panda_log() -> Resource:
    """
    Stream the current Panda log file as a resource.
    """
    if not os.path.exists(LOG_PATH):
        return Resource(
            uri="panda://run_panda.log",
            name="Panda log (not found)",
            mime_type="text/plain",
            content="Log file not yet created."
        )

    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        data = f.read()[-5000:]  # tail the last ~5 KB to keep it light
    return Resource(
        uri="panda://run_panda.log",
        name="Panda log",
        mime_type="text/plain",
#       content=data  # returns one long line with "\n" in
        content=[{"type": "text", "text": data}]
    )

# DEBUG
@mcp.tool()
def test_stream():
    for i in range(5):
        print(f"STREAM {i}", file=sys.stderr, flush=True)
        time.sleep(1)
    return {"done": True}

if __name__ == "__main__":
    mcp.run()



