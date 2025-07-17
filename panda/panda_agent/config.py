
import os

#PANDA_LLM = 'gpt-4.1'
PANDA_LLM = 'claude'
REPORT_WRITER_LLM = PANDA_LLM
REPORT_TRANSLATOR_LLM = PANDA_LLM	# convert HTML to text (not used now I think)

SUPERPANDA_LLM = 'gpt-4.1'
SUPERPANDA_REPORT_WRITER_LLM = SUPERPANDA_LLM

ITERPANDA_LLM = 'gpt-4.1'	# relies on class...

# Get the directory where my_globals.py is located
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))		# panda/panda/panda_agent
ROOT_DIR = os.path.dirname(os.path.dirname(MODULE_DIR))		# panda/

# ==================================================
# Globals for main Panda
# ==================================================

# Read in the system prompt template
SYSTEM_PROMPT_TEMPLATE_FILE = os.path.join(MODULE_DIR, "panda_agent_prompt_template.txt")
SYSTEM_PROMPT_TEMPLATE_FILE_ALLOW_SHORTCUTS = os.path.join(MODULE_DIR, "panda_agent_prompt_template_allow_shortcuts.txt")

# Panda builds the prompt dynamically and caches it here for the user's benefit
SYSTEM_PROMPT_FILE = os.path.join(MODULE_DIR, "panda_agent_prompt.txt")

ADVICE_FILE = os.path.join(MODULE_DIR, "advice.txt")

# ----------

VERSION_FILE = os.path.join(MODULE_DIR, "../../VERSION")	# bit ugly, peeking out of the package directory....
with open(VERSION_FILE, 'r') as f:
    VERSION = f.read()    

# ----------

doc = {}		 # Place to put docstring for write_report.write_report()
MAX_RETRIES = 2
MAX_EARLIER_STEP_RETRIES = 2
MAX_ITERATIONS = 200     # prevent runaway system!
EXEC_TIMEOUT = 3600	 # 60 min max for executing a function, otherwise give up. This better be long enough!

PANDA_HEADER = "============================== Panda =============================="
SYSTEM_PROMPT_HEADER   = "============================ SYSTEM PROMPT ==========================="
GPT_HEADER = "================================ {PANDA_LLM} ================================="
CODING_START = "Coding thoughts:\n"
PYTHON_START = "---------- START PYTHON ENVIRONMENT ----------\n"
CODING_END   = "----------- END PYTHON ENVIRONMENT -----------\n\n"


