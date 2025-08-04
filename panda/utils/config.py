
import os

doc = {}

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Go to inferd.allen.ai to renew INFERD token
INFERD_TOKEN = os.environ.get("INFERD_TOKEN")

if OPENAI_API_KEY is None:
    print("Please set your OPENAI_API_KEY environment variable to continue!")
if TOGETHER_API_KEY is None:
    print("Please set your TOGETHER_API_KEY environment variable if you want to use Mistral and/or Llama!")
if INFERD_TOKEN is None:
    print("Please set your INFERD_TOKEN environment varaiable if you want to use OLMo!")
if ANTHROPIC_API_KEY is None:
    print("Please set your ANTHROPIC_API_KEY environment varaiable if you want to use Clude!")    

# keys and models
OAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

#OLMO_ENDPOINT = 'https://ai2-reviz--olmoe-1b-7b-0924-instruct.modal.run/completion'  # updated 10/16/24
OLMO_ENDPOINT = "https://inferd.allen.ai/api/v1/infer"
#OLMO_VERSION_ID = 'mov_01j1x1awwfqx23gmw0wkmb73ea'
OLMO_VERSION_ID = 'mov_01j74syrtad9dyfkc7zm4jrske'    # olmo-7b-chat

TOGETHER_ENDPOINT = "https://api.together.xyz/v1/chat/completions"

# Not yet working
TULU_ENDPOINT = "https://inferd.allen.ai/api/v1/infer"
TULU_VERSION_ID = 'mov_01j1djbjemksstnx5ws82emhqs'

# Now accessed through litellm
LLAMA_MODEL = "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
MISTRAL_MODEL = "together_ai/mistralai/Mistral-7B-Instruct-v0.2"

#DEFAULT_GPT4_MODEL = 'gpt-4-1106-preview'
#DEFAULT_GPT4_MODEL = 'gpt-4o'
#DEFAULT_GPT4_MODEL = 'gpt-4.1-nano'
DEFAULT_GPT4_MODEL = 'gpt-4.1'
DEFAULT_GPT45_MODEL = 'gpt-4.5-preview-2025-02-27'
#DEFAULT_CLAUDE_MODEL = "claude-3-5-sonnet-20240620"
#DEFAULT_CLAUDE_MODEL = "claude-3-7-sonnet-latest"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"

MAX_GPT_ATTEMPTS = 3
MAX_OLMO_ATTEMPTS = 3
MAX_TOGETHER_ATTEMPTS = 6    # Llama can be a bit more flakey
MAX_LITELLM_ATTEMPTS = 3

TOGETHER_TIMEOUT = 30
OLMO_TIMEOUT = 60
#GPT_TIMEOUT = 60
GPT_TIMEOUT = 300
GPT45_TIMEOUT = 300
O1_TIMEOUT = 120

    

