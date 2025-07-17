
import os

# global var to store the tool documentation in
doc = {}


LLM_AS_JUDGE = 'gpt4'

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
FUNCTION_DOC_FILE = os.path.join(MODULE_DIR, "documentation_functions.txt")
WORKFLOW_DOC_FILE = os.path.join(MODULE_DIR, "documentation_workflows.py")
PLAN_DOC_FILE = os.path.join(MODULE_DIR, "documentation_plans.txt")

# THESE KEYS USED FOR LITERATURE SEARCH FUNCTIONALITY, CURRENTLY NOT PART OF THE GITHUB RELEASE

# LLM keys are in utils/config.py, as LLM utilities are shared by both panda and researchworld

S2_API_KEY = os.environ.get("S2_API_KEY")
if S2_API_KEY is None:
    print("Optional: Please set your S2_API_KEY environment variable (if you want to use paper search functions)!")

# ==================================================
# Globals for literature search - Not in use yet
# ==================================================

ARXIV_PDF_URL = "http://arxiv.org/pdf/"
PAPER_DIRECTORY = os.path.abspath(os.path.join(MODULE_DIR, "../papers/"))     # abs to factor out ".." in the path string
if not os.path.exists(PAPER_DIRECTORY):
    os.makedirs(PAPER_DIRECTORY)

# For AI2I paper search
BIFROEST_ENDPOINT = "https://bifroest-staging.allen.ai/api/1/dense-search"
BIFROEST_DATASET = "arxiv-acl"
BIFROEST_VARIANT = "e5"

PAPER_FINDER_ENDPOINT = "https://mabool-demo.allen.ai"
PAPER_FINDER_QUERY_ENDPOINT = PAPER_FINDER_ENDPOINT + "/api/2/rounds"

S2_BASE_URL = "https://api.semanticscholar.org/graph/v1/"


