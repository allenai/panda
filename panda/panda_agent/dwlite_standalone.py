
"""
DEMO

In [46]: %run dwlite_standalone.py

In [47]: dialog = []				# initialize. Initial val is irrelevant, and can treat dialog as a latent (uninteresting) variable hiding the full dialog with the simulator

In [48]: observation1 = start_dwlite(dialog)	# e.g., -> "colonists are getting sick. Why?"

In [49]: print(observation1)

You are in the common area of the habitation module on Planet X. A colonist has just complained of feeling queasy after eating some local food, and the mission commander has asked you to investigate what's going on and prevent future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with instruments, medical bay, and other colonists who can be interviewed.


In [50]: action1 = "Go and interview the colonist"	# or whatever your AI system thinks you should do next

In [51]: observation2 = do_dwlite_action(dialog, action1) # e.g, -> "You visit the colonist and she says she's sick"

In [52]: print(observation2)
You walk over to the nearby table where the colonist, Dr. Lin, is sitting and looking a bit pale. She sips water and glances up as you approach.

When you ask about her symptoms, she replies:  
- "I started feeling nauseous and got a mild headache about 30 minutes after lunch."
- "It's happened a couple of times now, always after eating some of the local produce."
- "Today I had a salad with hydroponic tomatoes and greens, plus some bread from the kitchen."

She adds that other colonists have mentioned similar stomach issues recently, but not everyone seems affected.

Dr. Lin looks willing to answer more questions or help with your investigation.

In [53]: action2 = ... etc. etc.

"""

import os
import re
from string import Template
import requests

DEFAULT_GPT_MODEL = 'gpt-4.1'
DWLITE_PROMPT_TEMPLATE_FILE = 'dwlite_prompt_template.txt'
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
MAX_GPT_ATTEMPTS = 3
GPT_TIMEOUT = 300

if OPENAI_API_KEY is None:
    print("Please set your OPENAI_API_KEY environment variable to continue!", file=sys.stderr)

# ----------

default_scenario_for_user = """"
You are in the common area of the habitation module on Planet X. A colonist has just complained of feeling queasy after eating some local food, and the mission commander has asked you to investigate what's going on and prevent future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with instruments, medical bay, and other colonists who can be interviewed.
"""

# ----------

default_scenario_for_system = """
### **2. Current Quest: Space Illness (Space Sick Theme)**
The current task is the **Space Illness** challenge.
High-level premise for the player:
* Some colonists occasionally feel mildly ill (e.g., nausea, stomach upset, headache) after eating local food from Planet X.
* The player's goal is to determine **what is causing the illness** and **implement a fix** so that future colonists no longer get sick from this cause.

Hidden ground truth (for you, the simulator):
* A subset of the local food has become **contaminated with mold**.
* Mold contamination can:

  * Be seen directly with certain instruments (e.g., microscope, mold-stain test, special culture plate).
  * Be detected indirectly via abnormal readings from other instruments (e.g., a spectrometer showing anomalous peaks).
  * Be inferred behaviorally (e.g., contaminated food becomes safe once thoroughly cooked, while uncooked portions still cause illness).

* Do not introduce any **distractor signals** that indicate another cause - keep it simple for now.
"""
"""
======================================================================
		DISCOVERYWORLD-LITE
======================================================================

"""
def start_dwlite(dialog, scenario_for_system=default_scenario_for_system, scenario_for_user=default_scenario_for_user):
    with open(DWLITE_PROMPT_TEMPLATE_FILE, 'r') as f:
        dwlite_prompt_template = Template(f.read())
    dwlite_prompt = dwlite_prompt_template.substitute({'scenario_for_system':scenario_for_system, 'scenario_for_user':scenario_for_user})
    dialog.clear()
    dialog.append(dwlite_prompt)    
#    my_print(dwlite_prompt, 'Superpanda')
    starting_scene = simple_call_gpt(dialog)
    dialog.append(starting_scene)
#    my_print(starting_scene, SUPERPANDA_LLM)
    return scenario_for_user
# do_dwlite_action(dialog, "Go and interview the colonist")
# do_dwlite_action(dialog, 'Extract secondary metabolites from the local food using organic solvents (methanol, ethanol, acetone) and analyze the extracts using available analytical techniques such as chromatography, mass spectrometry, or spectrophotometry to identify potential toxins')
# -> 
def do_dwlite_action(dialog, action):
    dialog.append(action)
#    my_print(action, 'Superpanda')
    response = simple_call_gpt(dialog)
    dialog.append(response)
#    my_print(response, SUPERPANDA_LLM)
    response_body = strip_trailing_question(response)
    return response_body

# ======================================================================
#		UTILITIES
# ======================================================================

def my_print(text, role="?"):
    print(f"================================ {role} =================================")
    print(text)

def strip_trailing_question(text: str) -> str:
    """
    Removes the final trailing question (including Markdown formatting) 
    if the final sentence is a question. Returns the cleaned text.
    """
    original = text.rstrip()

    # Pattern to capture a trailing question sentence (optionally wrapped in markdown)
    # Handles cases like:
    #   What do you want to do next?
    #   **What do you want to do next?**
    #   *What do you want to do next?*
    #   ## What do you want to do next?
    md_opt = r'(?:[*_#\s]*)'   # Optional markdown stars, underscores, headers, spaces
    question_pattern = (
        rf"{md_opt}"           # Leading markdown
        r"([^\n]*\?)"          # The question sentence
        rf"{md_opt}$"          # Optional markdown after
    )

    # Try to find a final question at the end
    match = re.search(question_pattern, original)

    if match:
        # Remove the entire matched question block
        cleaned = original[:match.start()].rstrip()
        return cleaned

    # If no terminal question found, return original text
    return original

### ======================================================================
### 		UTILITIES
### ======================================================================

def simple_call_gpt(prompt, response_format="text", temperature=0, openai_api_key=OPENAI_API_KEY, quiet=True, model=DEFAULT_GPT_MODEL):

    prompts = (
        prompt if isinstance(prompt, list) else
        [prompt] if isinstance(prompt, str) else
        (print(f"DEBUG: ERROR! Unrecognized prompt format {prompt}") or None)
    )    
    url = OAI_ENDPOINT
    model = DEFAULT_GPT_MODEL if model=="gpt4" else model
    max_tokens = "max_tokens" if model.startswith("gpt-4") else "max_completion_tokens"		# latter for o1
    temperature1 = 1 if model.startswith("o1") else temperature
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {openai_api_key}'
    }
    messages = convert_to_messages(prompts, model=model)
    data = {
        'model': model,
        'messages': messages,
        'temperature': temperature1,
        max_tokens: 4000,
    }

    if not model.startswith("o1"):
        data['top_p'] = 0.5  # Only add 'top_p' if model is NOT o1*
        data['presence_penalty'] = 0.5
        data['frequency_penalty'] = 0.5
        data['response_format'] = {'type':response_format}
        
    for attempt in range(0,MAX_GPT_ATTEMPTS):
        try:
            if not quiet:
                print("DEBUG: prompts =", prompts)
            response = requests.post(url, headers=headers, json=data, timeout=GPT_TIMEOUT)
            response_json = response.json()
            if not quiet:
                print("DEBUG: Response = ", response_json)
            
            # Check if there's an error in the response
            if 'error' in response_json:
                raise ValueError(response_json['error']['message'])
            
            # Extract the content based on the response format
            if response_format == "json_object":
                content = response_json['choices'][0]['message']['content']
            else:
                content = response_json['choices'][0]['message']['content']
            return content
        except Exception as e:
            print(f"ERROR from {model}: {e}. Trying again...")
    
    # If all attempts fail
    print(f"ERROR from {model}: Giving up completely after {MAX_GPT_ATTEMPTS} tries (returning NIL)")
    return ""

### ======================================================================

"""
Convert a list of strings showing a 2-way conversation, e.g., 
convert_to_messages(["You are a helpful assistant.","Hi","How can I help?","What is your name?"]) -> 
[{'role': 'system', 'content': 'You are a helpful assistant.'},
 {'role': 'user', 'content': 'Hi'},
 {'role': 'system', 'content': 'How can I help?'},
 {'role': 'user', 'content': 'What is your name?'}]
"""
def convert_to_messages(input_data, model=DEFAULT_GPT_MODEL, first_role="system"):      # first_role = "user" for non-GPT

    SYSTEM_PROMPT = "You are a helpful assistant."
    if isinstance(input_data, str):
        input_data = [input_data]

    if len(input_data) % 2 != 0:
        input_data = [SYSTEM_PROMPT] + input_data

    json_data = []
    role = "assistant"				# just the FIRST message is "system" for GPT
    for i in range(0, len(input_data), 2):
        if i == 0:
            json_data.append({'role': first_role, 'content': input_data[i]})	# first role may be "user" (LiteLLM) or "system" (GPT)
        else:
            json_data.append({'role': role, 'content': input_data[i]})
        json_data.append({'role': 'user', 'content': input_data[i+1]})
        role = "assistant"    # anything after the first role is "assistant"
    return json_data

