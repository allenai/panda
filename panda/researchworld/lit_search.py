
"""
 ======================================================================
 	LITERATURE SEARCH TOOLS
 ======================================================================
  find_paper_ids(query, top_k) -> list of corpus_ids (that have associated paper text)
  get_paper_text(corpus_id) -> full text (str)
  summarize_paper(corpus_id) -> paragraph summary (str)
  ask_paper(corpus_id, question) -> answer (str)
  get_paper_details(corpus_id, fields=["title","authors","year","venue"]) -> list of paper JSONs (list of {'title':..., 'authors':...})

For example:
  paper_info = panda.researchworld.lit_search.find_paper_ids("Ideation by language models")
    -> [{'corpus_id': '238353829', 'title': 'AI Chains...'} {'corpus_id': '267406608', 'title': '...'}, ...]
  corpus_ids = panda.researchworld.lit_search.get_corpus_ids(paper_info)
    -> ['238353829','267406608',...]
  corpus_id = corpus_ids[0]
    -> '238353829'
  details = get_paper_details(corpus_id, fields=["title","authors","year","venue"])
    -> {'title':'AI Chains: Transparent and ....', 'year':2021, 'authors':...}
  summary = panda.researchworld.lit_search.summarize_paper(corpus_id)
    -> "The paper is focused on the area of Human-AI Interaction, ..."
"""

import os
import sys
import requests
import json
import time
from functools import lru_cache

from . import config     # leave "config." prefix on for now, for clarity
from panda.utils import call_llm, clean_extract_json, file_exists, read_file_contents, convert_pdf_to_text, download_file, logger

### ======================================================================
###		PAPER SEARCH
### ======================================================================

config.doc['find_paper_ids'] = """
def find_paper_ids(search_query:str, top_k:int):
Purpose:
    Find technical papers (corpus_ids) using search_query as the search term.
Args:
    search_query (str): A string to search with, e.g., "theory of mind", "papers combining symbolic an neural reasoning", etc.
    top_k (int): Optional argument (default 2), specifying how many papers to return
Returns:
    list (str): List of CorpusIDs
Example:
    print(find_paper_ids("theory of mind", top_k=2))
->  ['253098632','3454285']
"""
# Also: method (str): One of ['paper_finder_infer', 'paper_finder_fast']. This controls how much search to do (slow/fast).
def find_paper_ids(search_query=None, top_k=10, method='paper_finder_infer'):
    cached_results = find_paper_ids_cached(search_query, top_k, method)
    if cached_results is None:
        return None 
    logger.info(f"{len(cached_results)} papers found.")
    return cached_results

@lru_cache()						    # To cache results, need to return a tuple (not a list of dicts)
def find_paper_ids_cached(search_query=None, top_k=10, method='paper_finder_infer'):
    if method in ['paper_finder_fast', 'paper_finder_infer']:
        mode = 'fast' if method == 'paper_finder_fast' else 'infer'
        results = call_paper_finder(search_query, top_k=top_k, mode=mode)	# [{'corpus_id':'23','title':'My title'},...]
        corpus_ids = get_corpus_ids(results)
        if len(corpus_ids) <= 10:
            return [corpus_id for corpus_id in corpus_ids if get_paper_text(corpus_id)]	# return just corpus_ids with associated text
        else:
            return corpus_ids				# don't filter for large number of responses
    else:
        raise ValueError(
            f"ERROR! 'method' argument to find_paper_ids should be 'bifroest' or 'paper_finder_fast' or 'paper_finder_infer', but was '{method}'")

# ----------    

def call_paper_finder(search_query=None, top_k=10, mode='infer'):
    if top_k == 0:
        return []
    else:
        url = config.PAPER_FINDER_QUERY_ENDPOINT
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
        location_url = config.PAPER_FINDER_ENDPOINT + location
        results = poll_paper_finder_answers(location_url, top_k)
        return results

# ----------

def poll_paper_finder_answers(location_url, top_k=10, max_attempts=20, interval=10):
    headers = {
        'accept': 'application/json'
        }
    attempts = 0
    print("Calling paper finder service...", end="", file=sys.stderr)
    while attempts < max_attempts:
        time.sleep(interval)
        try:
            response = requests.get(location_url, headers=headers)	# note GET, not POST
            response_json = json.loads(response.text)
            logger.info("")
            return response_json['document_results'][:top_k]		# [{'corpus_id':..., 'title':'...'}, ...]
        except Exception as e:  # Catch any exception
            attempts += 1
#           logger.info(f"Attempt {attempts} failed with exception: {e}. Retrying in {interval} seconds...")
#           logger.info(f"[ paper_finder still working... will poll again in {interval} seconds...]")
            print(".", end="", file=sys.stderr)						# show progress...
            
    logger.info(f"Yikes! paper_finder still not finished after {max_attempts * interval} seconds! Giving up....")
    return []  # All attempts failed

# ======================================================================
#		DOWNLOAD A PAPER 
# ======================================================================

config.doc['get_paper_text'] = """
def get_paper_text(corpus_id):
Purpose:
    Download the full text of a paper (if available). This downloads the PDF and converts it to plain text.
    While the plain text may be a bit mangled, it's fine as input to a downstream LLM, e.g., summarize_paper()
    NOTE: results are cached in the PAPER_DIRECTORY for faster re-querying. If the text or PDF is missing, returns "".
Args:
    corpus_id (str): The corpus ID of the paper to downloaded
Returns:
    paper_text (str): The plain text contents of the paper
Example:
    text = get_paper_text('238353829')
    print(text)
 -> 'AI Chains: Transparent and Controllable Human-AI Interaction\nby Chaining Large Language Model... [lots of text!]'
"""
def get_paper_text(corpus_id):
    paper_txt_file = os.path.join(config.PAPER_DIRECTORY, corpus_id + ".txt")
    paper_pdf_file = os.path.join(config.PAPER_DIRECTORY, corpus_id + ".pdf")
    paper_url = None
    paper_text = None

    if file_exists(paper_txt_file):				#
        logger.info(f"({corpus_id} is already cached)")
        paper_text = read_file_contents(paper_txt_file)
        return paper_text
    
    else:
        if file_exists(paper_pdf_file):
            logger.info(f"({corpus_id} already downloaded)")
        else:
            downloaded = download_paper_pdf(corpus_id, destination=paper_pdf_file)
            if downloaded == False:				# will be None if download temporarily blocked
                open(paper_txt_file, "w").close()		# create empty file
                return ""

        if file_exists(paper_pdf_file):	# download successful
            logger.info("Converting PDF to plain text...")
            convert_pdf_to_text(corpus_id, config.PAPER_DIRECTORY)

            paper_text = read_file_contents(paper_txt_file)
            return paper_text

# ----------        

# returns True (download succeeded), False (download not possible), or None (download temporarily failed)
def download_paper_pdf(corpus_id, destination):

    # (a) arXiv papers...
    if is_arxiv_id(corpus_id):
        paper_url = config.ARXIV_PDF_URL + corpus_id + ".pdf"
        logger.info(f"Downloading arXiv:{corpus_id}...")
        download_file(paper_url, destination)	# TO ADD: suppose this fails?
        return True

    # (b) Corpus papers...    
    paper_data_json = get_paper_details(corpus_id)
    if paper_data_json.get("isOpenAccess"):
        url_data_json = paper_data_json.get("openAccessPdf")
        if url_data_json:
            paper_url = url_data_json.get("url")
            paper_title = paper_data_json.get("title")
            logger.info(f"Downloading CorpusID:{corpus_id} {paper_title}...")
            download_file(paper_url, destination)	# TO ADD: suppose this fails?                
            return True
        else:
            logger.info(f"CorpusID:{corpus_id} doesn't seem to have an associated URL - can't download.")
            return False
    elif "isOpenAccess" in paper_data_json:		# will have value False
        logger.info(f"CorpusID:{corpus_id} is not Open Access - can't download.")
        return False
    elif paper_data_json == {}:
        logger.info("No details retrievable from S2 (Rate limits blocking?) - giving up...")
        return None
    else:
        logger.info("Failed to get paper for some unknown reason!")
        return None            

# ----------

# arxiv_ids are identified by having a "." in them, e.g., "2310.13648"
def is_arxiv_id(corpus_id):
    return "." in corpus_id

# ======================================================================
# 	SUMMARIZE A PAPER
# ======================================================================

config.doc['summarize_paper'] = """
def summarize_paper(corpus_id:str):
Purpose: 
    Summarize the contents of an arXiv technical paper.
Args:
    corpus_id (str): The arXiv ID of the paper to summarize, e.g., "2410.13648"
Returns:
    summary (str): A summary of the paper's contents, summarizing the papers context, overall content, hypothesis, related work, example problem, and findings. By printing the summary, that summary is brought into the conversation.
Side effect:
    The summary is also cached in a the config.PAPER_DIRECTORY    
Example:
    print(summarize_paper("2410.13648"))
    --------------------------------------------------
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
    paper_summary_file = os.path.join(config.PAPER_DIRECTORY, corpus_id + "-summary.txt")
    id_type = "arXiv" if is_arxiv_id(corpus_id) else "CorpusID" 
    
    if file_exists(paper_summary_file):				#
        logger.info(f"(Summmary of {id_type}:{corpus_id} is already cached)")
        with open(paper_summary_file, 'r') as file:
            return file.read()        
    else:        
        text = get_paper_text(corpus_id)
        if text:
            prompt =  SUMMARY_PRETEXT_PROMPT + text + SUMMARY_POSTTEXT_PROMPT
            logger.info(f"Summarizing paper {id_type}:{corpus_id}...")
            response = call_llm(prompt)
            response = "\n--------------------------------------------------\n          Summary of paper\n--------------------------------------------------\n\n" + response
#           with open(paper_summary_file, "w") as f:
            with open(paper_summary_file, "w", encoding="utf-8") as f:
                f.write(response)
            return response
        else:
#           logger.info(f"(No text found or {id_type}:{corpus_id})")
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
###		PAPER QA
### ======================================================================

config.doc['ask_paper'] = """
def ask_paper(corpus_id:str, question:str):
Purpose: 
    Have an LLM answer the question about the paper with corpus_id
Args:
    corpus_id (str): The arXiv ID of the paper to summarize, e.g., "2410.13648"
    question (str): The question or prompt to pose to the paper text
Returns:
    answer (str): The answer to the question
Example:
    print(ask_paper('2410.13648', "What are the main themes in this paper?"))
"""
def ask_paper(corpus_id, question):
    paper_text = get_paper_text(corpus_id)
    if not paper_text:
        logger.info(f"ERROR! Paper {corpus_id} has no associated text!")
        return ""
    prompt = """Read the following paper then ask the question at the end:
======================================================================
        START OF PAPER	
======================================================================
""" + paper_text + """
======================================================================
        END OF PAPER	
======================================================================
Now concisely answer the following question about the paper:
""" + question
    return call_llm(prompt)

### ======================================================================
###		PAPER DETAILS
### ======================================================================

config.doc['get_paper_details'] = """
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
    url = config.S2_BASE_URL
    service = "paper/"
    paper = "CorpusId:" + str(corpus_id)
    http_call = url + service + paper + "?fields=" + ",".join(fields)
    headers = {
        'Content-Type': 'application/json',
#       'Authorization': f'Bearer {config.S2_API_KEY}'
        'x-api-key': config.S2_API_KEY
    }
    for attempt in range(0,max_retries):
        try:
            response = requests.get(http_call, headers=headers)
            response_str = response.text
            response_json = clean_extract_json(response_str)
            if "code" in response_json and response_json["code"] == "429":  # Rate limited
                logger.info(f"Rate limited (429). Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)  # Pause before retrying
                continue  # Go to the next iteration of the loop (try again)
            elif response.status_code!= 200: # Any other bad status
                logger.info(f"S2 Error {response.status_code} for CorpusId {corpus_id}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)  # Pause before retrying
                continue  # Go to the next iteration of the loop (try again)
            else:
                break     # from the for... loop and continue
        except requests.exceptions.RequestException as e:  # Catch network errors
            logger.info(f"Request exception: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
        except json.JSONDecodeError as e:  # Catch JSON errors
            logger.info(f"JSON decode error: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
        except Exception as e: # Catch any other exception
            logger.info(f"An unexpected error has occurred: {e}. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
            time.sleep(retry_delay)
            continue
    else:  # Loop finished without success (all retries exhausted)
        logger.info(f"Max retries ({max_retries}) reached for corpus ID: {corpus_id}. Giving up...")
        response_json = {}
    
#   logger.info("Success!! response_json = %s", response_json)
    return response_json

### ======================================================================

# get_corpus_ids([{'corpus_id':'234','title':'My title'}]) -> ['234']
def get_corpus_ids(paper_jsons):
    corpus_ids=[]
    for paper_json in paper_jsons:
        if 'corpus_id' in paper_json:
            corpus_ids += [paper_json['corpus_id']]
        elif 'arxiv' in paper_json:
            corpus_ids += [paper_json['arxiv']]
        else:
            logger.info("ERROR! Can't find corpus_id or arxiv in the below paper JSON. Skipping...\n%s", paper_json)
    return corpus_ids

### ----------

class MaxRetriesExceeded(Exception):  # Custom exception - duplicate of class in utils/ask_llm.py, rather than do an import
    pass


    
