"""
USAGE:
$ conda create -n my_environment
$ conda activate my_environment
(my_environment) $ pip install pdfminer.six requests openai
(my_environment) $ ipython
In [1]: %load_ext autoreload
In [2]: %autoreload 2
In [3]: %run lit_search_standalone.py
In [4]: testit()

 ======================================================================
 	LITERATURE SEARCH TOOLS
 ======================================================================
  find_papers(query, top_k) -> list of paper JSONs (list of {'corpus_id':INT, 'title':STR} structures)
  get_corpus_ids(paper_jsons) -> list of corpus_ids
  get_paper_text(corpus_id) -> full text (str)
  summarize_paper(corpus_id) -> paragraph summary (str)
  get_paper_details(corpus_id, fields=["title","authors","year","venue"]) -> list of paper JSONs (list of {'title':..., 'authors':...})
and also:
  simple_call_gpt(prompt) -> answer (str)

For example:
"""
def testit():
    paper_info = find_papers("Ideation by language models")
    print("paper_info =", paper_info)    #  -> [{'corpus_id': '238353829', 'title': 'AI Chains...'} {'corpus_id': '267406608', 'title': '...'}, ...]
    corpus_ids = get_corpus_ids(paper_info)
    print("corpus_ids =", corpus_ids)    #  -> ['238353829','267406608',...]
    corpus_id = corpus_ids[0]		 #  -> '238353829'
    paper_full_text = get_paper_text(corpus_id)
    print("paper_full_text (first 60 chars) =", paper_full_text[:60], "...") 
    details = get_paper_details(corpus_id, fields=["title","authors","year","venue"])
    print("details =", details)	 	 #  -> {'title':'AI Chains: Transparent and ....', 'year':2021, 'authors':...}
    summary = summarize_paper(corpus_id)
    print("summary =", summary) 	 #  -> "The paper is focused on the area of Human-AI Interaction, ..."

import os
import requests
import json
import time
import unicodedata
from functools import lru_cache
from pdfminer.high_level import extract_text

# ==================================================
# 	CONFIGURATION PARAMETERS
# ==================================================

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
S2_API_KEY = os.environ.get("S2_API_KEY")

if OPENAI_API_KEY is None:
    print("Please set your OPENAI_API_KEY environment variable to continue!")
if S2_API_KEY is None:
    print("Optional: Please set your S2_API_KEY environment variable (if you want to use paper search functions)!")

OAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
PAPER_FINDER_ENDPOINT = "https://mabool-demo.allen.ai"
PAPER_FINDER_QUERY_ENDPOINT = PAPER_FINDER_ENDPOINT + "/api/2/rounds"
S2_BASE_URL = "https://api.semanticscholar.org/graph/v1/"

MAX_GPT_ATTEMPTS = 3
GPT_TIMEOUT = 30
PAPER_DIRECTORY = "papers/"			# where to cache the retrieved papers!
if not os.path.exists(PAPER_DIRECTORY):
    os.makedirs(PAPER_DIRECTORY)
ARXIV_PDF_URL = "http://arxiv.org/pdf/"

DEFAULT_GPT_MODEL = 'gpt-4-1106-preview'

### ======================================================================
###		PAPER SEARCH
### ======================================================================

"""
def find_papers(search_query:str, top_k:int, method='paper_finder_infer')
Purpose:
    Find arXiv technical papers using search_query as the search term.
Args:
    search_query (str): A string to search with, e.g., "theory of mind", "papers combining symbolic an neural reasoning", etc.
    top_k (int): Optional argument (default 2), specifying how many papers to return
    method (str): One of ['paper_finder_infer', 'paper_finder_fast']. This controls how much search to do (slow/fast).
Returns:
    [{'corpus_id':INT, 'title':STR},...,] (list of dicts): Each dict contains the corpus_id and title of the paper.
Example:
    print(find_papers("theory of mind", top_k=2))
->  [{'corpus_id': '253098632', 'title': 'Neural Theory-of-Mind? On the Limits of Social Intelligence in Large LMs'},
     {'corpus_id': '3454285', 'title': 'Machine Theory of Mind'}]
"""
def find_papers(search_query=None, top_k=10, method='paper_finder_infer'):
    cached_result = find_papers_cached(search_query, top_k, method)
    if cached_result is None:
        return None 
    results = [dict(item) for item in cached_result]	    # Convert the tuple back to a listof dicts
    return results

@lru_cache()						    # To cache results, need to return a tuple (not a list of dicts)
def find_papers_cached(search_query=None, top_k=10, method='paper_finder_infer'):
    if method in ['paper_finder_fast', 'paper_finder_infer']:
        mode = 'fast' if method == 'paper_finder_fast' else 'infer'
        results = call_paper_finder(search_query, top_k=top_k, mode=mode)
        return tuple(tuple(sorted(item.items())) for item in results)   # convert to tuples, so @lru_cache works
    else:
        raise ValueError(
            f"ERROR! 'method' argument to find_papers should be 'bifroest' or 'paper_finder_fast' or 'paper_finder_infer', but was '{method}'")

# ----------    

def call_paper_finder(search_query=None, top_k=10, mode='infer'):
    if top_k == 0:
        return []
    else:
        url = PAPER_FINDER_QUERY_ENDPOINT
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'            
        }
        data = {
            'paper_description': search_query,
            'caller_actor_id': 'panda_caller_id',  
            'operation_mode': mode
        }
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response_headers = response.headers
        location = response_headers['location']
        location_url = PAPER_FINDER_ENDPOINT + location
        results = poll_paper_finder_answers(location_url, top_k)
        return results

# ----------

def poll_paper_finder_answers(location_url, top_k=10, max_attempts=20, interval=10):
    headers = {
        'accept': 'application/json'
        }
    attempts = 0
    print("Calling paper finder service...", end="")
    while attempts < max_attempts:
        time.sleep(interval)
        try:
            response = requests.get(location_url, headers=headers)	# note GET, not POST
            response_json = json.loads(response.text)
            print()
            return response_json['document_results'][:top_k]		# [{'corpus_id':..., 'title':'...'}, ...]
        except Exception as e:  # Catch any exception
            attempts += 1
#           print(f"Attempt {attempts} failed with exception: {e}. Retrying in {interval} seconds...")
#           print(f"[ paper_finder still working... will poll again in {interval} seconds...]")
            print(".", end="")						# show progress...
            
    print(f"Yikes! paper_finder still not finished after {max_attempts * interval} seconds! Giving up....")
    return []  # All attempts failed

# ======================================================================
#		DOWNLOAD A PAPER 
# ======================================================================
"""
def get_paper_text(corpus_id):
Purpose:
    Download the full text of a paper (if available). This downloads the PDF and converts it to plain text.
    While the plain text may be a bit mangled, it's fine as input to a downstream LLM, e.g., summarize_paper()
    NOTE: results are cached in the PAPER_DIRECTORY for faster re-querying
Args:
    corpus_id (str): The corpus ID of the paper to downloaded
Returns:
    paper_text (str): The plain text contents of the paper
Example:
    get_paper_text('238353829')
 -> 'AI Chains: Transparent and Controllable Human-AI Interaction\nby Chaining Large Language Model...'
    (a LARGE block of text!)
"""
def get_paper_text(corpus_id):
    paper_txt_file = os.path.join(PAPER_DIRECTORY, corpus_id + ".txt")
    paper_pdf_file = os.path.join(PAPER_DIRECTORY, corpus_id + ".pdf")
    paper_url = None
    paper_text = None

    if file_exists(paper_txt_file):				#
        print(f"({corpus_id} is already cached)")
        paper_text = read_file_contents(paper_txt_file)
        return paper_text
    
    else:
        if file_exists(paper_pdf_file):
            print(f"({corpus_id} already downloaded)")
        else:
            download_paper_pdf(corpus_id, destination=paper_pdf_file)

        if file_exists(paper_pdf_file):	# download successful
            print("Converting PDF to pain text...")
            convert_pdf_to_text(corpus_id, PAPER_DIRECTORY)

            paper_text = read_file_contents(paper_txt_file)
            return paper_text

# ----------        

def download_paper_pdf(corpus_id, destination):

    paper_url = None
    
    # 1. find the paper URL
    if is_arxiv_id(corpus_id):
        id_type = "arXiv"
        paper_url = ARXIV_PDF_URL + corpus_id + ".pdf"
    else:
        id_type = "CorpusID"
        paper_data_json = get_paper_details(corpus_id)
        if paper_data_json.get("isOpenAccess"):
            url_data_json = paper_data_json.get("openAccessPdf")
            if url_data_json:
                paper_url = url_data_json.get("url")
            else:
                print(f"{id_type}:{corpus_id} doesn't seem to have an associated URL - can't download.")
        else:
            print(f"{id_type}:{corpus_id} is not Open Access (or not recognized by S2) - can't download.")
                

    # 2. download it                    
    if paper_url:                    
        print(f"Downloading {id_type}:{corpus_id}...")
        download_file(paper_url, destination)	# TO ADD: suppose this fails?

# ----------

# arxiv_ids are identified by having a "." in them, e.g., "2310.13648"
def is_arxiv_id(corpus_id):
    return "." in corpus_id

# ======================================================================
# 	SUMMARIZE A PAPER
# ======================================================================

"""
def summarize_paper(corpus_id:str):
Purpose: 
    Summarize the contents of an arXiv technical paper.
Args:
    corpus_id (str): The arXiv ID of the paper to summarize, e.g., "2410.13648"
Returns:
    summary (str): A summary of the paper's contents, summarizing the papers context, overall content, hypothesis, related work, example problem, and findings. By printing the summary, that summary is brought into the conversation.
Example:
    print(summarize_paper("2410.13648"))
            Summary of paper
    --------------------------------------------------
    Title: SIMPLETOM: EXPOSING THE GAP BETWEEN EXPLICIT TOM INFERENCE AND IMPLICIT TOM APPLICATION IN LLMS
    Authors: Yuling Gu, Ronan Le Bras, Oyvind Tafjord, Peter Clark, Hyunwoo Kim, Yejin Choi, Jared Moore
    1. Context:
    The paper is focused on the area of AI that deals with large language models (LLMs)...
    2. Summary:
    ....
"""
# summarize_paper("2410.13648")	# Yuling's ToM paper. text is the optional contents 
def summarize_paper(corpus_id=None):
    paper_summary_file = os.path.join(PAPER_DIRECTORY, corpus_id + "-summary.txt")
    id_type = "arXiv" if is_arxiv_id(corpus_id) else "CorpusID" 
    
    if file_exists(paper_summary_file):				#
        print(f"(Summmary of {id_type}:{corpus_id} is already cached)")
        with open(paper_summary_file, 'r') as file:
            return file.read()        
    else:        
        text = get_paper_text(corpus_id)
        if text:
            prompt =  SUMMARY_PRETEXT_PROMPT + text + SUMMARY_POSTTEXT_PROMPT
            print(f"Summarizing paper {id_type}:{corpus_id}...")
            response = simple_call_gpt(prompt)
            response = "    Summary of paper\n--------------------------------------------------\n\n" + response
            with open(paper_summary_file, "w") as f:
                f.write(response)
            return response
        else:
#           print(f"(No text found or {id_type}:{corpus_id})")
            return None

SUMMARY_PRETEXT_PROMPT = """
First read the following paper:

======================================================================
                   START OF PAPER
======================================================================
"""

SUMMARY_POSTTEXT_PROMPT = """
======================================================================
                   END OF PAPER
======================================================================

Now summarize the following information:

Title: Give the title of the paper
Authors: List the paper's authors (You do not need to list their affiliations)

1. Context: Describe the general area of AI that the paper is working on

2. Summary

Provide a bulleted summary of the paper, in 5-10 bullets.

3. Hypothesis

Describe the main hypothesis that is being tested in the paper.

4. Related Work

Provide a bulleted summary of the related work described in the paper, in 5-10 bullets.

5. Example Problem

Provide a complete example of the kind of problem/question/test used in the experiments. The example should be standalone, and not depend on unstated context. I should be able to then generate more examples similar to this so that I can reproduce the experiments that the authors describe.

6. Findings

Provide a bulleted summary of the main findings of the paper.
"""
    
### ======================================================================
###		PAPER SUMMARIZATION
### ======================================================================

"""
def get_paper_details(corpus_id:str, fields=["title","isOpenAccess","openAccessPdf"], max_retries=10)o
Purpose:
    Retrieve details about a paper given its corpus id
Args:
    corpus_id (str): The S2 corpus id, e.g., '253098632'
    fields (list of str): The information to get. Available fields are listed here:
           https://api.semanticscholar.org/api-docs/#tag/Paper-Data/operation/get_graph_get_paper
        and include: title, authors, abstract, year, venue, tldr, citations, referenceCount, citationCount, 
        influentialCitationCount, isOpenAccess, openAccessPdf
Returns:
    A JSON dict of field:value pairs for each field requested
Example:
    get_paper_details('253098632', ['title','authors','yeaar','venue'])
->  {'paperId': '311fd5f6f114ae51f8cbd95a0da69d7b556d25f1',
     'title': 'Neural Theory-of-Mind? On the Limits of Social Intelligence in Large LMs',
     'year': 2022,
     'venue': 'Conference on Empirical Methods in Natural Language Processing',
     'authors': [{'authorId': '2729164', 'name': 'Maarten Sap'}, {'authorId': '39227408', 'name': 'Ronan Le Bras'}, ...]}
"""                                   
def get_paper_details(corpus_id:str, fields=["title","isOpenAccess","openAccessPdf"], max_retries=10):
    retry_delay = 1 # second
    url = S2_BASE_URL
    service = "paper/"
    paper = "CorpusId:" + str(corpus_id)
#   fields = ["url","year"]
#   fields = ["title","isOpenAccess","openAccessPdf"]
    http_call = url + service + paper + "?fields=" + ",".join(fields)
    headers = {
        'Content-Type': 'application/json',
#       'Authorization': f'Bearer {S2_API_KEY}'
        'x-api-key': S2_API_KEY        
    }
#   print("DEBUG: http_call =", http_call)
    for attempt in range(0,max_retries):
        try:
            response = requests.get(http_call, headers=headers)
            response_str = response.text
            response_json = json.loads(response_str)  # Parse the JSON string            
            if "code" in response_json and response_json["code"] == "429":  # Rate limited
                print(f"Rate limited (429). Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)  # Pause before retrying
                continue  # Go to the next iteration of the loop (try again)
            elif response.status_code!= 200: # Any other bad status
                print(f"S2 Error {response.status_code} for CorpusId {corpus_id}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)  # Pause before retrying
                continue  # Go to the next iteration of the loop (try again)
            else:
                break     # from the for... loop and continue
        except requests.exceptions.RequestException as e:  # Catch network errors
            print(f"Request exception: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
        except json.JSONDecodeError as e:  # Catch JSON errors
            print(f"JSON decode error: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
        except Exception as e: # Catch any other exception
            print(f"An unexpected error has occurred: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
    else:  # Loop finished without success (all retries exhausted)
        print(f"Max retries ({max_retries}) reached for corpus ID: {corpus_id}. Giving up...")
        response_json = {}
    
#   print("Success!! response_json =", response_json)
    return response_json

### ======================================================================

def get_corpus_ids(paper_jsons):
    corpus_ids=[]
    for paper_json in paper_jsons:
        if 'corpus_id' in paper_json:
            corpus_ids += [paper_json['corpus_id']]
        elif 'arxiv' in paper_json:
            corpus_ids += [paper_json['arxiv']]
        else:
            print("ERROR! Can't find corpus_id or arxiv in the below paper JSON. Skipping...\n", paper_json)
    return corpus_ids

### ----------

class MaxRetriesExceeded(Exception):  # Custom exception - duplicate of class in utils/ask_llm.py, rather than do an import
    pass

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

# ======================================================================
#		READ FILE 
# ======================================================================

def read_file_contents(filename):
  """
  Reads the entire contents of a text file into a string.
  Args:
    filename: The path to the text file.
  Returns:
    str: The contents of the file as a string.
    None: If the file cannot be opened.
  """
  try:
    with open(filename, 'r') as file:
      contents = file.read()
      return contents
  except FileNotFoundError:
    print(f"Error: File '{filename}' not found.")
    return None

"""
# Example usage:
file_path = "path/to/your/file.txt"  # Replace with the actual file path
file_contents = read_file_contents(file_path)

if file_contents:
  print(file_contents)
"""

# utility

def file_exists(path):
  return os.path.isfile(path)

# ======================================================================
# 		DOWNLOAD A FILE
# ======================================================================

def download_file(url=None, filepath=None):
    """
    Downloads a file from the given URL and saves it to the dir.
    Args:
        url (str): The URL of the file.
    Returns:
        str: The path to the downloaded file, or None if download fails.
    """
    try:
        # Download the file
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Save the file to the directory
        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath

    except Exception as e:
        print(f"Error downloading file from {url}: {e}")
        return None

### ======================================================================
###		CONVERT PDF TO TEXT
### ======================================================================

def convert_pdf_to_text(filestem, directory):
    # Construct the full paths to the PDF and the output text file
    pdf_path = os.path.join(directory, f"{filestem}.pdf")
    txt_path = os.path.join(directory, f"{filestem}.txt")
    
    # Check if the PDF file exists
    if not os.path.exists(pdf_path):
        print(f"PDF file '{pdf_path}' does not exist.")
        return
    
    try:
        # Extract text from the PDF file
        text = extract_text(pdf_path)
        print("DEBUG: cleaning now...")
        clean_text = replace_special_chars_with_ascii(text)
        
        # Write the text to the output text file
        with open(txt_path, 'w', encoding='utf-8') as txt_file:
            txt_file.write(clean_text)
        
        print(f"Successfully converted '{pdf_path}' to '{txt_path}'.")
    except Exception as e:
        print(f"An error occurred while converting the PDF: {e}")

# ======================================================================
#	GET RID OF SPECIAL CHARACTERS
# ======================================================================
    
# o1 version

CUSTOM_REPLACEMENTS = {
    8212: ' - ',   # Em dash
    8211: '-',     # En dash
    8220: '"',     # Left double quotation mark
    8221: '"',     # Right double quotation mark
    8216: "'",     # Left single quotation mark
    8217: "'",     # Right single quotation mark
    8230: '...'    # Ellipsis
    # Add more replacements as needed
}

def replace_special_chars_with_ascii(text):
    global CUSTOM_REPLACEMENTS
    result = []

    for char in text:
        code_point = ord(char)
        if code_point in CUSTOM_REPLACEMENTS:
            result.append(CUSTOM_REPLACEMENTS[code_point])
        else:
            normalized_char = unicodedata.normalize('NFKD', char)
            ascii_bytes = normalized_char.encode('ascii', 'ignore')
            ascii_char = ascii_bytes.decode('ascii')
            result.append(ascii_char)
    ascii_text = ''.join(result)
    return ascii_text


    
