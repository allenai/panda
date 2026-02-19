
import os

PANDA_LLM = "claude-sonnet-4-5-20250929"
REPORT_WRITER_LLM = PANDA_LLM
REPORT_TRANSLATOR_LLM = PANDA_LLM	# convert HTML to text (not used now I think)

SUPERPANDA_LLM = PANDA_LLM
SUPERPANDA_REPORT_WRITER_LLM = PANDA_LLM

ITERPANDA_LLM = PANDA_LLM	# relies on class...
STEPPANDA_LLM = PANDA_LLM	# relies on class...

# Get the directory where my_globals.py is located (i.e., panda_agent)
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))		# panda/panda/panda_agent
ROOT_DIR = os.path.dirname(os.path.dirname(MODULE_DIR))		# panda/panda/

# ==================================================
# Globals for main Panda
# ==================================================

# Read in the system prompt template
# NEW: No longer use library!
#SYSTEM_PROMPT_TEMPLATE_FILE = os.path.join(MODULE_DIR, "panda_agent_prompt_template.txt")
#SYSTEM_PROMPT_TEMPLATE_FILE = os.path.join(MODULE_DIR, "panda_agent_prompt_template_short.txt")
#SYSTEM_PROMPT_TEMPLATE_FILE_ALLOW_SHORTCUTS = os.path.join(MODULE_DIR, "panda_agent_prompt_template_allow_shortcuts.txt")

# Panda builds the prompt dynamically and caches it here for the user's benefit
# new: Now static, not dynamic
SYSTEM_PROMPT_FILE = os.path.join(MODULE_DIR, "panda_agent_prompt.txt")

ADVICE_FILE = os.path.join(MODULE_DIR, "advice.txt")

# ----------

from importlib.metadata import version
VERSION = version('panda')

# This is bad coding practice, as it requires an extra file; in addition, that file is not included in the site
# package when installed as a tool (the site package is only the panda/ subdirectory files)
#VERSION_FILE = os.path.join(MODULE_DIR, "../../VERSION")	# bit ugly, peeking out of the package directory....
#with open(VERSION_FILE, 'r') as f:
#    VERSION = f.read().strip() 

# ----------

doc = {}		 # Place to put docstring for write_report.write_report()
MAX_RETRIES = 2
MAX_EARLIER_STEP_RETRIES = 2
MAX_ITERATIONS = 200     # prevent runaway system!
#EXEC_TIMEOUT = 3600	 # 60 min max for executing a function, otherwise give up. This better be long enough!
#EXPERIMENT_TIMEOUT = 7200	 # 2 hr max for an experiment
#EXPERIMENT_TIMEOUT = 10800	 # 3 hr max for an experiment
EXPERIMENT_TIMEOUT = 40000	 # lots!!

PANDA_HEADER = "============================== Panda =============================="
SYSTEM_PROMPT_HEADER   = "============================ SYSTEM PROMPT ==========================="
GPT_HEADER = "================================ {PANDA_LLM} ================================="
CODING_START = "Coding thoughts:\n"
PYTHON_START = "---------- START PYTHON ENVIRONMENT ----------\n"
CODING_END   = "----------- END PYTHON ENVIRONMENT -----------\n\n"

