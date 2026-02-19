"""
Clear cache:
panda.utils.ask_llm.cached_call_gpt.cache_clear()

TEST CASES:
panda.utils.call_llm("What is 1 + 1?", "llama")

panda.utils.call_llm_json("What is 1 + 1? Return your answer as a JSON structure {'answer':NUMBER}.")
Out[24]: '{\n  "answer": 2\n}'     - note you then have to subsequently parse this with json.loads(answer)

panda.utils.call_llm("What is 1 + 1?")
Out[21]: '1 + 1 equals 2.'
"""

import requests
import json
import time
import math	# for math.ceil in _truncate_string_middle_by_words()

from unidecode import unidecode
from functools import lru_cache
from litellm import completion

# Use of Pydantic classes for Structured Output in GPT
from pydantic import BaseModel
from openai import OpenAI

from . import config			# import entire file
from .utils import clean_extract_json	# import function
from .logger import logger, with_quiet_logging
from panda.panda_agent import config as agent_config

# e.g., [{ "model":"gpt-4.1","prompt_tokens": 85932,"completion_tokens": 18386,"total_tokens": 104318}, ...]
token_counts = []

def reset_token_counts():
    global token_counts
    token_counts = []

# we'll ignore the GPT versioning for now
def get_token_counts():
    return token_counts

class MaxRetriesExceeded(Exception):  # Custom exception
    """Raised when the maximum number of retries is reached."""
    pass  # No additional attributes needed in this case

# Define the OAI client for GPT. This appears to use a bunch of system variables (e.g., OPENAI_API_KEY)
client = OpenAI()

""" 
======================================================================
 		CALL LLM
======================================================================
Note: if prompt is a list of messages, then model must be a GPT
"""

config.doc['call_llm'] = f"""
def call_llm(prompt:str, model:str, temperature:float=0):
Purpose:
    Basic access to an LLM.
Args:
    prompt (str): The question/instruction to give to the LLM.
    model (str): One of {config.MODEL_NAMES}
    temperature (int): The temperature to use during LLM generation (default 0)
Returns:
    response (str): The LLM response.
Example:
    call_llm("Generate a new research idea about large language models.")
->  Title: Investigating the Impact of Multimodal Inputs on Large Language ....
"""
def call_llm(prompt, response_format={"type":"text"}, model=agent_config.PANDA_LLM, temperature=0, quiet=True):
#   logger.debug(f"DEBUG: Calling model {model}...")
#   if temperature > 0:
#        logger.debug(f"DEBUG: call_llm with temperature = {temperature}\nprompt = {repr(prompt[:50])}...")
    if model == "olmo":
        answer =  call_olmo(prompt, temperature=temperature, quiet=quiet)
    elif model in ["gpt4",config.DEFAULT_GPT4_MODEL]:
        answer =  call_gpt(prompt, response_format=response_format, temperature=temperature, model=config.DEFAULT_GPT4_MODEL, quiet=quiet)
    elif model in ["gpt4.5",config.DEFAULT_GPT45_MODEL]:
        answer =  call_gpt(prompt, response_format=response_format, temperature=temperature, model=config.DEFAULT_GPT45_MODEL, quiet=quiet)
#   elif model in ["o1-mini","o3-mini","o4-mini","gpt-4.1","gpt-4.1-nano","gpt-5","gpt-5-mini"]:        
    elif model.startswith(("o1", "o3", "o4", "gpt")):
        answer =  call_gpt(prompt, response_format=response_format, temperature=temperature, model=model, quiet=quiet)
    elif model == "llama":
        answer =  call_litellm(prompt, config.LLAMA_MODEL, quiet=quiet)
    elif model == "mistral":									# Need a MISTRAL_API_KEY for this
        answer =  call_litellm(prompt, config.MISTRAL_MODEL, quiet=quiet)
    elif model == "claude":
        answer =  call_litellm(prompt, config.DEFAULT_CLAUDE_MODEL, quiet=quiet)
    elif model == "claude-3.5":
        answer =  call_litellm(prompt, config.CLAUDE35_MODEL, quiet=quiet)
    elif model.startswith(("claude", "llama", "meta", "mistral")):
        answer =  call_litellm(prompt, model, quiet=quiet)        		# NEW: Allow any LiteLLM to be explicitly specified
    else:
        logger.error(f"Unrecognized model: {model}")
        answer =  f"Unrecognized model: {model}"

# This is a bit of a sledgehammer that can remove some important characters. ChatGPT suggests unidecode instead which tries an ascii approximation.
# https://chatgpt.com/share/68b086e0-ad2c-8001-bb07-6d5d60cc4c16
#   return answer.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")    	# Remove encoding errors
    return unidecode(answer)

### ======================================================================

"""
def call_llm_json(prompt:str, response_format=None, model:str):
Purpose:
    Return a JSON object from a query to GPT
Args:
    prompt (str|list): The prompt to be sent to GPT. (can alternatively be a list of messages)
    response_format (dict or Pydantic class): (optional) The JSON schema to return for GPT's answer. If missing, specify the JSON in prompt.
    model (str): The LLM to call. Currently must be one of {config.JSON_CAPABLE_MODEL_NAMES}
Returns:
    JSON object (json): json_template instantiated with GPT's answer
    string (str): the string representation of the JSON object
Example:
    print(call_llm_json('What is Obama\'s first name and age? Return a JSON of the form {{"first_name":FIRST_NAME, "age":INTEGER}}'))
    -> (   {{'first_name': 'Barack', 'age': 61}},
           '{{"first_name":"Barack","age":61}}'    )
"""
def call_llm_json(prompt, response_format={"type":"json_object"}, temperature=0, max_retries=3, model=agent_config.PANDA_LLM):
    for attempt in range(0,max_retries):
        try:
            if attempt == 0:
                response_str = call_llm(prompt, temperature=temperature, response_format=response_format, model=model)
            else:
                extra_advice = "\nPlease respond concisely (your previous answer was too long to process!)\n"
                if isinstance(prompt, str):
                    prompt += extra_advice
                elif isinstance(prompt, list):
                    prompt[-1] += extra_advice
                response_str = call_llm(prompt, response_format=response_format, temperature=0.7, model=model)	# make sure we get a different answer
            return clean_extract_json(response_str), response_str
        except Exception as e:
            logger.warning(f"{model} exception {e}. (invalid JSON structure?)....retrying...")
    else:
        raise MaxRetriesExceeded("Max retries reached...giving up...")

### ======================================================================

"""
Example:
    print(call_llm_multiple_choice("I hit someone for fun. Was that wrong?", ["wrong","not_wrong"], model='olmo'))
->  wrong
"""
def call_llm_multiple_choice(prompt, options, max_retries=3, model=agent_config.PANDA_LLM, quiet=True):

    prompt += f" (Your answer options are {options})"

    if model not in ['gpt4',config.DEFAULT_GPT4_MODEL]:			# For non-GPT, we need to split QA and JSON building separately (see multiple_choice_issue.txt)
        # first answer unconstrained
        response = call_llm(prompt, model=model)

        # then use GPT to convert to JSON
        json_prompt = f'Now summarize the last response as a JSON object with the following stucture {{"answer":CHOICE}}, where CHOICE is exactly one of {options}'
        dialog = [prompt, response, json_prompt]
    else:
        dialog = prompt + f'\nReturn your answer as a JSON object with the following stucture {{"answer":CHOICE}}, where CHOICE is exactly one of {options}'
    
    for attempt in range(0,max_retries):
        try:
            if attempt == 0:
                response,_ = call_llm_json(dialog, model='gpt4')
            else:
                response,_ = call_llm_json(dialog, temperature=0.7, model='gpt4')
            if 'answer' not in response:
                logger.warning(f"Yikes! No 'answer' field in GPT response {response}....Trying again...")
            else:
                answer = response['answer']
                if answer in options:
                    return answer
                else:
                    logger.warning(f"Yikes! GPT gave answer '{answer}' but that isn't one of the options {options}!. Trying again...")
        except Exception as e:
            logger.warning(f"GPT exception {e}. (invalid JSON structure?)....retrying...")
    else:
        raise MaxRetriesExceeded("Max retries reached...giving up...")

### ======================================================================
###		OLMO
### ======================================================================

def raw_call_olmo(prompt, temperature=0, inferd_token=config.INFERD_TOKEN, quiet=True):
    # quiet currently unused
    url = config.OLMO_ENDPOINT
    model_version_id = config.OLMO_VERSION_ID
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {inferd_token}'
    }
    data = {
        'model_version_id': model_version_id,
        'input': {
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'opts': {
                'temperature': temperature,
#                'max_tokens': 1000,		 don't need this?
                'logprobs': 2
            }
        }
    }

    for attempt in range(0,config.MAX_OLMO_ATTEMPTS):
        try:
            logger.debug("DEBUG: OLMo data = %s", json.dumps(data))
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=config.OLMO_TIMEOUT)
            response_lines = response.text.strip().split('\n')
            logger.debug("DEBUG: response_lines = %s", response_lines)
            result_tokens = []
            for line in response_lines:
                line_json = json.loads(line)
                token = line_json.get('result', {}).get('output', {}).get('text', '')
                result_tokens.append(token)
            return ''.join(result_tokens)
        except Exception as e:
            logger.warning(f"ERROR from OLMo: {e}. Trying again...")                
    logger.error(f"ERROR from OLMo: Giving up completely after {config.MAX_OLMO_ATTEMPTS} tries (returning NIL)")
    return ""                    

def call_olmo(prompt, temperature=0, cache=True, inferd_token=config.INFERD_TOKEN, quiet=True):
#    global olmo_calls    
#    olmo_calls += 1        
    if cache:
        return cached_call_olmo(prompt, temperature=temperature, inferd_token=inferd_token, quiet=quiet)
    else:
        return raw_call_olmo(prompt, temperature=temperature, inferd_token=inferd_token, quiet=quiet)

# Apply the lru_cache decorator
@lru_cache() 
def cached_call_olmo(prompt, temperature=0, inferd_token=config.INFERD_TOKEN, quiet=True):
    return raw_call_olmo(prompt, temperature=temperature, inferd_token=inferd_token, quiet=quiet)

# Example:
# "The capital of England is London"

# ======================================================================

# Tulu endpoint no longer available it seems....
def raw_call_tulu(prompt, temperature=0, inferd_token=config.INFERD_TOKEN, quiet=True):
    # quiet currently unused
    url = config.TULU_ENDPOINT
    model_version_id = config.TULU_VERSION_ID
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {inferd_token}'
    }
    data = {
        'model_version_id': model_version_id,
        'input': {
            'messages': [{
                'role': 'user',
                'content': prompt
            }],
            'opts': {
                'temperature': temperature,
#                'max_tokens': 1000,	- don't need this?
                'logprobs': 2
            }
        }
    }

    for attempt in range(0,config.MAX_OLMO_ATTEMPTS):
        try:
            logger.debug("DEBUG: headers = %s", headers)
            logger.debug("DEBUG: data = %s", data)            
            response = requests.post(url, headers=headers, data=json.dumps(data), timeout=config.OLMO_TIMEOUT)
            response_lines = response.text.strip().split('\n')
            logger.debug("DEBUG: response_lines = %s", response_lines)
            result_tokens = []
            for line in response_lines:
                line_json = json.loads(line)
                token = line_json.get('result', {}).get('output', {}).get('text', '')
                result_tokens.append(token)
            return ''.join(result_tokens)
        except Exception as e:
            logger.warning(f"ERROR from OLMo: {e}. Trying again...")                
    logger.error(f"ERROR from OLMo: Giving up completely after {config.MAX_OLMO_ATTEMPTS} tries (returning NIL)")
    return ""                    

# ======================================================================

# panda.utils.ask_llm.call_litellm("What is your name?") -> "I don't have a name"
# [1] GPT says this is better than what I did for call_gpt(), namely:
#            response_json = response.json()
#            content = response_json['choices'][0]['message']['content']
#     because the dot-notation is cleaner, safer, refactorable (https://chatgpt.com/share/688ac049-7f10-8001-8dd5-3cb4f5e96f91)
def call_litellm(prompts0, model=config.DEFAULT_CLAUDE_MODEL, quiet=True):

    def max_words(model):
        return 80000		# default. claude-3-5-sonnet-20240620 I believe is 200k tokens (100k words was too many so reduced to 80k)
    
    prompts1 = (
        prompts0 if isinstance(prompts0, list) else
        [prompts0] if isinstance(prompts0, str) else
        (logger.debug(f"DEBUG: ERROR! Unrecognized prompt format {prompts0}") or None)
    )            

#   prompts = truncate_prompt(prompts1, truncate_from=8, max_words=max_words(model))
    prompts = truncate_prompt(prompts1, max_words=max_words(model))    
    messages = convert_to_messages(prompts, model=model, first_role="user")

    for attempt in range(0,config.MAX_LITELLM_ATTEMPTS):
        try:
            if not quiet:
                logger.debug("DEBUG: prompts = %s", prompts)
#           response = completion(model=model, messages=messages)
            response = with_quiet_logging(completion, model=model, messages=messages)	# suppress LiteLLM logs which mess up MCP stream somehow
            if response and response.choices and response.choices[0].message and response.choices[0].message.content:
                content = response.choices[0].message.content		# [1]                
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                total_tokens = response.usage.total_tokens                
                add_token_counts(model, prompt_tokens, completion_tokens, total_tokens)                

                return content
            else:
                logger.warning(f"Not getting the right response structure from {model}. Trying again...")               
        except Exception as e:
            logger.warning(f"ERROR from {model}: {e}. Trying again...")
    
    # If all attempts fail
    logger.error(f"ERROR from {model}: Giving up completely after {config.MAX_LITELLM_ATTEMPTS} tries (returning '')")
    return ""

# ======================================================================

# response_format = {"type":"text"}, {"type":"json_object"} [obsolete],
# or <abbreviated-json-schema> that's expanded by build_gpt_response_format into {"type":"json_schema","json_schema":...}
def raw_call_gpt(prompts0, response_format={"type":"text"}, temperature=0, openai_api_key=config.OPENAI_API_KEY, quiet=True, model=config.DEFAULT_GPT4_MODEL):

#   logger.debug(f"DEBUG: Calling GPT with temperature={temperature}, model={model}...")
#   logger.debug("DEBUG: response_format =", response_format)
#    input("pause...")
    ### estimate max word length (given max token length)
    def max_words(model=config.DEFAULT_GPT4_MODEL):
        if model in ['gpt-4-1106-preview','gpt-4o']:
            return 80000
        else:
            return 80000		# default

#    if isinstance(prompts0, list):
#        word_counts = [len(s.split()) for s in prompts0]
#        logger.debug("DEBUG: words per prompt message:", word_counts)

    prompts1 = (
        prompts0 if isinstance(prompts0, list) else
        [prompts0] if isinstance(prompts0, str) else
        (logger.debug(f"DEBUG: ERROR! Unrecognized prompt format {prompts0}") or None)
    )    
#   prompts = truncate_prompt(prompts1, truncate_from=8, max_words=max_words(model))   # handle GPT4's 128k token limit
    prompts = truncate_prompt(prompts1, max_words=max_words(model))   # handle GPT4's 128k token limit    
    first_role = "system" if model in ['gpt4','config.DEFAULT_GPT4_MODEL'] else "assistant"
    messages = convert_to_messages(prompts, model=model, first_role=first_role)
    
    url = config.OAI_ENDPOINT
    model = config.DEFAULT_GPT4_MODEL if model=="gpt4" else model
    max_tokens = "max_tokens" if model.startswith("gpt-4") else "max_completion_tokens"		# latter for o1
    is_reasoning_model = model.startswith("o") or model.startswith("gpt-5")
    temperature1 = 1 if is_reasoning_model else temperature
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {openai_api_key}'
    }

    data = {
        'model': model,
        'messages': messages,
        'temperature': temperature1
#        max_tokens: 4000,
    }

    if not is_reasoning_model:
        data['top_p'] = 0.5  # Only add 'top_p' if model is NOT o1* or o3*
        data['presence_penalty'] = 0.5
        data['frequency_penalty'] = 0.5
        data['response_format'] = response_format

    if is_reasoning_model:
        timeout = config.GPT_REASONING_TIMEOUT
    elif model in ["gpt4.5",config.DEFAULT_GPT45_MODEL]:
        timeout = config.GPT45_TIMEOUT
    else:
        timeout = config.GPT_TIMEOUT
        
    for attempt in range(0,config.MAX_GPT_ATTEMPTS):
        try:
            if not quiet:
                logger.debug("DEBUG: prompts = %s", prompts)

            if isinstance(response_format, type):			# Pydantic class
                if is_reasoning_model:
                    response=client.beta.chat.completions.parse(		# Pydantic structure response
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        temperature=temperature1,
#                        max_completion_tokens=4000,				# <=== distinction max_completion_tokens vs. max_tokens - now obsolete?
                        )
                else:                    
                    response=client.beta.chat.completions.parse(		# Pydantic structure response
                        model=model,
                        messages=messages,
                        response_format=response_format,
                        temperature=temperature1,
#                        max_tokens=4000,					# <===
                        )
                response_json = response.dict()
            else:
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
                response_json = response.json()
            if not quiet:
                logger.debug("DEBUG: Response = %s", response_json)
            
            # Check if there's an error in the response
            if 'error' in response_json:
                raise ValueError(response_json['error']['message'])

            content = response_json['choices'][0]['message']['content']
            prompt_tokens = response_json['usage']['prompt_tokens']
            completion_tokens = response_json['usage']['completion_tokens']
            total_tokens = response_json['usage']['total_tokens']
            add_token_counts(model, prompt_tokens, completion_tokens, total_tokens)

            return content

        except Exception as e:
            logger.warning(f"ERROR from {model}: {e}. Trying again...")
            time.sleep(1)            
    
    # If all attempts fail
    logger.error(f"ERROR from {model}: Giving up completely after {config.MAX_GPT_ATTEMPTS} tries (returning NIL)")
    return ""

# ---------- utility ----------

# Courtesy ChatGPT
def add_token_counts(model, prompt_tokens, completion_tokens, total_tokens):
    global token_counts  # Ensure we're modifying the global list
    # Search for an existing entry for the model
    for entry in token_counts:
        if entry['model'] == model:
            # Update existing token counts
            entry['prompt_tokens'] += prompt_tokens
            entry['completion_tokens'] += completion_tokens
            entry['total_tokens'] += total_tokens
            return
    # If model not found, append a new entry
    token_counts.append({
        'model': model,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': total_tokens
    })

# ======================================================================
#      Utility to allow abbreviated response format to be specified
# ======================================================================

"""
convert an abbreviated form of Structured Output to the full form.
https://platform.openai.com/docs/guides/structured-outputs
Models supported: gpt-4.5, o1* o3*, gpt-4o
In [1]: build_gpt_response_format({"location":{"type":"string"},"temperature":{"type":"string"}}) 
{ "type": "json_schema",
  "json_schema": {
    "name": "dummy",
    "description": "dummy",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "location": {"type": "string"},
        "temperature": {"type": "string"}}
      },
      "additionalProperties": false,
      "required": ["location","temperature"]}}}
"""
def build_gpt_response_format(response_format, name="dummy", description="dummy"):

    if response_format in [{"type":"text"},{"type":"json_object"}]:
        return response_format

    elif isinstance(response_format, dict):
        full_response_format = {
            "type":"json_schema",
            "json_schema":{
                "name":name,				# ok to have all schemas called the same thing?
#               "description":description,
                "strict":True,
                "schema":{
                    "type":"object",
                    "properties":response_format,		# e.g., {"location":{"type":"string","description":"..."},"
                    "additionalProperties":False,
                    "required":list(response_format.keys())
                }}}
        return full_response_format

    else:
        raise ValueError(f'build_gpt_response_format(): argument must be "text", "json_object", or a dict! But was {response_format}.')

# ----------

"""
def call_gpt(prompt:str, response_format="text", model=config.DEFAULT_GPT4_MODEL):
Purpose:
    Ask/instruct GPT for something
Args:
    prompt (str): The question/instruction to give GPT
    response_format (str): either "text" or "json_object". If you want a JSON object response, the prompt needs to explicitly say so, and describe the desired JSON structure of the response.
Returns:
    response (str): The GPT response. If a JSON structure is expected, you should subsequently convert from string to JSON using json.loads(response)
Example (response_format="text"):
    print(call_gpt("Generate a new research idea about large language models."))
->  Title: Investigating the Impact of Multimodal Inputs on Large Language Model Performance and Generalization
    Abstract: ...
Example (response_format="json_object"):
    response = call_gpt('What is the largest state capital in the USA? Return your answer as JSON in the form {"capital":CAPITAL, "state":STATE}', response_format="json_object")
    print("response =", repr(response), "\njson.loads(response) = ", json.loads(response))
->  response = '{"capital":"Phoenix", "state":"Arizona"}'                 # a string
    json.loads(response) = {"capital":"Phoenix", "state":"Arizona"}       # a JSON object
"""
def call_gpt(prompts, response_format={"type":"text"}, temperature=0, cache=True, openai_api_key=config.OPENAI_API_KEY, quiet=True, model=config.DEFAULT_GPT4_MODEL):
    
#   global gpt_calls
    if cache and temperature == 0:
        response = cached_call_gpt(convert_to_hashable(prompts), response_format=convert_to_hashable(response_format),
                                   temperature=temperature, openai_api_key=openai_api_key, quiet=quiet, model=model)	# Lists not directly hashable
    else:
        response = raw_call_gpt(prompts, response_format=response_format, temperature=temperature, openai_api_key=openai_api_key, quiet=quiet, model=model)
#    gpt_calls += 1        
    return response        

# Apply the lru_cache decorator
# To clear the cache:
#     research_utils.ask_llm.cached_call_gpt.cache_clear()
@lru_cache() 
def cached_call_gpt(prompts, response_format, temperature=0, openai_api_key=config.OPENAI_API_KEY, quiet=True, model=config.DEFAULT_GPT4_MODEL):
    return raw_call_gpt(convert_from_hashable(prompts), response_format=convert_from_hashable(response_format), temperature=temperature, openai_api_key=openai_api_key, quiet=quiet, model=model)

# ------------------------------
# Can't hash dicts, only tuples so need to convert
# ------------------------------

def convert_to_hashable(obj):
    if isinstance(obj, dict):
#       return tuple(sorted((k, convert_to_hashable(v)) for k, v in obj.items()))  - don't bother sorting, keep order it was written in
        return tuple((k, convert_to_hashable(v)) for k, v in obj.items())
    elif isinstance(obj, list):
        return tuple(convert_to_hashable(x) for x in obj)
    else:
        return obj

def convert_from_hashable(obj):
    if isinstance(obj, tuple):
        if all(isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in obj):
            return {k: convert_from_hashable(v) for k, v in obj}
        else:
            return [convert_from_hashable(item) for item in obj]
    else:
        return obj

### ======================================================================

"""
Convert a list of strings showing a 2-way conversation, e.g., 
convert_to_messages(["You are a helpful assistant.","Hi","How can I help?","What is your name?"]) -> 
[{'role': 'system', 'content': 'You are a helpful assistant.'},
 {'role': 'user', 'content': 'Hi'},
 {'role': 'system', 'content': 'How can I help?'},
 {'role': 'user', 'content': 'What is your name?'}]
"""
# model is unused
def convert_to_messages(input_data, model, first_role="system"):      # first_role = "user" for non-GPT
    """
    Converts a list of strings representing a 2-way conversation to a JSON structure.
    Args:
        input_data: A list of strings or a single string representing the conversation.
    Returns:
        A list of dictionaries, each representing a message with 'role' and 'content' keys.
    """
    SYSTEM_PROMPT = "You are a helpful, rigorous science assistant."

    if isinstance(input_data, str):
        input_data = [input_data]

    if len(input_data) % 2 != 0:
        input_data = [SYSTEM_PROMPT] + input_data

    json_data = []
#   role = "system" if model in ["gpt-4o","gpt-4-1106-preview"] else "assistant"
    role = "assistant"				# just the FIRST message is "system" for GPT
    for i in range(0, len(input_data), 2):
        if i == 0:
            json_data.append({'role': first_role, 'content': input_data[i]})	# first role may be "user" (LiteLLM) or "system" (GPT)
        else:
            json_data.append({'role': role, 'content': input_data[i]})
        json_data.append({'role': 'user', 'content': input_data[i+1]})
        role = "assistant"    # anything after the first role is "assistant"
    return json_data

### ======================================================================
###		TRUNCATING PROMPTS IF TOKEN COUNT EXCEEDED
### ======================================================================
# courtesy ChatGPT

'''
def old_truncate_prompt(lst, truncate_from=5, max_words=1000):
    """
    Truncate a list of strings to ensure the total token count is less than max_words.

    Parameters:
    - lst (list of str): List of strings to truncate.
    - truncate_from (int): Index to start truncating pairs of elements from.
    - max_words (int): Maximum allowed number of tokens (approximate word count).

    Returns:
    - list: Truncated list of strings.
    """
    # Ensure input is valid
    if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
        raise ValueError("lst must be a list of strings.")

    if count_tokens_in_stringlist(lst) < max_words:
        return lst	    # avoid doing a shallow copy unless necessary	
    else:
        lst2 = list(lst)    # copy, so as not to destructively change lst
        # Check the current token count
        while count_tokens_in_stringlist(lst2) > max_words:
            # Determine the pair of elements to replace
            if len(lst2) <= truncate_from:
                break  # Nothing to replace beyond this point
            replace_index = truncate_from
            truncate_from = truncate_from + 2   # 
            
            # Replace two elements with '...' if possible
            if replace_index + 1 < len(lst2):
                lst2[replace_index] = '...'
                lst2[replace_index + 1] = '...'
            else:
                lst2[replace_index] = '...'
#    print("Final count:", count_tokens_in_stringlist(lst2))                
    return lst2
'''

def count_tokens_in_stringlist(strings):
    """Helper function to count the approximate number of tokens in a list of strings."""
    return sum(len(s.split()) for s in strings)

'''
# Example usage
example_list = [
    "This is the first string.",
    "Here is another one.",
    "And yet another string.",
    "This list keeps going.",
    "More strings follow.",
    "We need to truncate from here.",
    "Extra strings to test.",
    "More and more strings.",
]

In [83]: print(truncate_prompt(example_list, truncate_from=2, max_words=25))
['This is the first string.', 'Here is another one.', '...', '...', '...', '...', 'Extra strings to test.', 'More and more strings.']
'''

# ======================================================================
#		UPDATED TRUNCATE VERSION (ChatGPT)
# ======================================================================
"""
REVISED VERSION: Simply remove words from the start, if necessary. We need to preserve the query (at the end)
 and the most recent context surrounding it.

Write me a function to truncate a prompt (list of strings) so it contains max_words or less, with signature:
	def truncate_prompt(list, max_words=2, ellipsis="...")
The function should remove words from the *start* if there are more than max_words. For example, if
  list = ["Here is a sentence.", "And here is another.","And another."]
truncate_prompt(list, max_words=2) -> ["...","...","And another."]
truncate_prompt(list, max_words=4) -> ["...","...is another.","And another."]
truncate_prompt(list, max_words=8) -> ["...a sentence.","And here is another.","And another."]
truncate_prompt(list, max_words=12) -> ["Here is a sentence.","And here is another.","And another."]
"""
def truncate_prompt(lst, max_words=2, ellipsis="..."):
    """
    Truncate a list of strings so the total number of words is <= max_words.
    Words are removed from the start. The removed portion is replaced with `ellipsis`.

    Args:
        lst (list[str]): List of strings (prompt segments).
        max_words (int): Maximum number of words allowed in the result.
        ellipsis (str): String used to mark removed text.

    Returns:
        list[str]: Truncated list of strings.
    """
    # Split each string into words
    split_lines = [line.split() for line in lst]
    all_words = [w for line in split_lines for w in line]

    # If already within the limit, return unchanged
    if len(all_words) <= max_words:
        return lst

    # Calculate how many words to drop
    drop_count = len(all_words) - max_words

    # Rebuild lines while dropping from the start
    result = []
    words_removed = 0
    for line in split_lines:
        if words_removed + len(line) <= drop_count:
            # Entire line is removed
            result.append(ellipsis)
            words_removed += len(line)
        else:
            # Partially remove this line
            keep_from = drop_count - words_removed
            new_line = " ".join(line[keep_from:])
            if keep_from > 0:
                new_line = ellipsis + new_line[len(line[keep_from-1]):] if new_line else ellipsis
                new_line = ellipsis + new_line if not new_line.startswith(ellipsis) else new_line
            result.append(new_line)
            # Copy the rest of the lines unchanged
            idx = split_lines.index(line)
            for rest in split_lines[idx+1:]:
                result.append(" ".join(rest))
            break

    return result

# ======================================================================
"""
***OLD VERSION*** - but we need to preserve the final query!!

example_list = [
    "This is the first string, and it is very long indeed and has lots of words in it, in fact too many than we need.",
    "Here is another one.",
    "And yet another string.",
    "This list keeps going.",
    "More strings follow.",
    "We need to truncate from here.",
    "Extra strings to test.",
    "More and more strings.",
]
Delete strings after truncate_from to the end to get size down to max_words. If still too long, chop middle sections of start words.
truncate_from = 2, max_words =:
2  ['...', '...']
4  ['This ...', 'Here ...']
10 ['This is ... we need.', 'Here is another one.']
30 ['This is the first string, and it ... in fact too many than we need.', 'Here is another one.']
35 ['This is the first string, and it is very long indeed and has lots of words in it, in fact too many than we need.', 'Here is another one.', '...', '...', '...', '...', '...', '...']
50 ['This is the first string, and it is very long indeed and has lots of words in it, in fact too many than we need.', 'Here is another one.', '...', '...', 'More strings follow.', 'We need to truncate from here.', 'Extra strings to test.', 'More and more strings.']
"""

def OLD_truncate_prompt(lst, truncate_from=5, max_words=1000, ellipsis="..."):
    """
    Truncate a list of strings so the approximate total word count does not exceed max_words.
    - Preserve the first `truncate_from` strings as long as possible.
    - Replace later items in pairs with '...' until under the limit.
    - If the first `truncate_from` strings alone still exceed max_words,
      drop all later items and truncate each of those `truncate_from` strings
      by chopping the *middle* so each is at most floor(max_words / truncate_from) words.

    Notes:
    - If max_words < truncate_from, at least one word per preserved string is impossible;
      this function will cap each preserved string to at least 1 ¡°word¡± (the ellipsis),
      so the total may still exceed max_words in a strict tokenizer sense.
    """
    # Validate input
    if not isinstance(lst, list) or not all(isinstance(x, str) for x in lst):
        raise ValueError("lst must be a list of strings.")

    # You provided this elsewhere; assumed to return an approximate word count for the list.
    def _fallback_count_tokens_in_stringlist(seq):
        # fallback: count words by whitespace
        return sum(len(s.split()) for s in seq)

    # Use your counter if available; otherwise, use the fallback.
    try:
        total = count_tokens_in_stringlist(lst)  # noqa: F821  # your project function
        counter = count_tokens_in_stringlist     # noqa: F821
    except NameError:
        total = _fallback_count_tokens_in_stringlist(lst)
        counter = _fallback_count_tokens_in_stringlist

    if total <= max_words:
        return lst

    lst2 = list(lst)  # non-destructive

    # Phase 1: collapse items after `truncate_from` in pairs into an ellipsis
    replace_index = truncate_from
    while counter(lst2) > max_words and replace_index < len(lst2):
        if replace_index + 1 < len(lst2):
            lst2[replace_index] = ellipsis
            lst2[replace_index + 1] = ellipsis
        else:
            lst2[replace_index] = ellipsis
        replace_index += 2

    # Phase 2: if still over the budget, focus only on the first `truncate_from` strings
    if counter(lst2) > max_words:
        # Drop everything after the preserved region entirely
        lst2 = lst2[:truncate_from]

        # Compute per-string cap and truncate each individually by chopping the middle
        # Use floor to guarantee total <= max_words (in word-count approximation).
        per_string_cap = max(1, max_words // max(1, truncate_from))
        lst2 = [
            _truncate_string_middle_by_words(s, per_string_cap, ellipsis=ellipsis)
            for s in lst2
        ]

        # (Optional) If your tokenizer counts '...' as multiple tokens and you need to be extra strict,
        # you could add a final tightening pass here.

    return lst2


def _truncate_string_middle_by_words(s: str, max_words_per_string: int, ellipsis: str = "...") -> str:
    """Keep the start and end, remove the middle, inserting an ellipsis."""
    if max_words_per_string <= 0:
        return ""  # nothing fits
    words = s.split()
    if len(words) <= max_words_per_string:
        return s
    if max_words_per_string == 1:
        return ellipsis  # only room for the marker
    # allocate slots around the ellipsis
    keep_head = math.ceil((max_words_per_string - 1) / 2)
    keep_tail = (max_words_per_string - 1) // 2
    if keep_tail > 0:
        return " ".join(words[:keep_head] + [ellipsis] + words[-keep_tail:])
    else:
        return " ".join(words[:keep_head] + [ellipsis])



    
