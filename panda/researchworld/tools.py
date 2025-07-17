
"""
To make tools accessible in iPython at the top-level do: 

from panda.researchworld import *
from panda.utils import *
from panda.panda_agent import *
"""

import pandas as pd
import os

from panda.utils import llm_list, map_dataframe, map_dataframe_json, map_dataframe_multiple_choice
from . import config                                   # access config.doc var
from panda.utils import config as utils_config      # access config.doc var in the sibling package

# global, to track what was built
created_datasets = []

config.doc['create_dataset'] = """
def create_dataset(prompt:str, item_col:str='question', temperature:int=0):
Purpose:
    Generate a dataset of items (e.g., questions) using prompt, and place in a new DataFrame under item_col
Args:
    prompt (str): The prompt querying GPT for dataset items. The prompt MUST mention the number of items to return.
        Note that items don't have be questions: they can also scenarios, situations, etc.
        It is good practice to include an example item (e.g., question) in the prompt.
    item_col (str) (optional, default 'question'): The column to put the items under
    temperature (int): The temperature to use during LLM generation (default 0)
Returns:
    DataFrame: A new dataframe containing the items
Example:
    dataset = create_dataset("Generate 30 test questions that test simple two-digit addition, e.g., '23 + 43 = ?'", item_col='question')
    print(dataset)
->     question
    0  35 + 47 = ?
    1  58 + 16 = ?
    2  72 + 29 = ?
    ...
Example:
    print(create_dataset("Generate 30 moral dilemmas, e.g., 'John was faced with stealing food to save his family.'", item_col='dilemma'))
->     dilemma
    0  A doctor must choose between saving a young child with a rare disease or using the limited medicine to save five elderly patients.
    1  An engineer knows about a flaw in a bridge's design that could lead to collapse but revealing it would cause panic and cost their job.
...
"""
def create_dataset(prompt, item_col='question', temperature:int=0):
    global created_datasets    
    questions = llm_list(prompt, temperature=temperature)
    dataset = pd.DataFrame({item_col: questions})
    print(dataset)
    created_datasets += [dataset]
    return dataset

# ----------------------------------------

config.doc['answer_questions'] = """
def answer_questions(dataset:pd.DataFrame, prompt_template:str, answer_col:str, model:str):
Purpose:
    For every row in the dataset, query the model with the instantiated prompt_template, and put answers under a new column called answer_col.
Args:
    dataset (DataFrame): the dataset, containing items (e.g., questions) under a particular column (e.g., 'question')
    prompt_template (str): The template prompt to query model with. The template reference the item column
    answer_col (str): The DataFrame column to place the answers in
    model (str): The model to query. For now, valid answers are 'gpt4', 'gpt-4.1', 'gpt-4.1-nano', 'olmo', 'llama', 'mistral', 'claude', 'o1-mini', 'o3-mini', 'o4-mini'
Returns:
    DataFrame: The dataset DataFrame updated with the answers. (Note: the dataset Dataframe is destructively updated)
Example:
    dataset = pd.DataFrame([{'question':'What is 1 + 1?'}, {'question':'What is 2 + 2?'}])
    answer_questions(dataset, "Answer this question: {question}", answer_col='answer', model='olmo')
    print(dataset)
 ->          question answer
    0  What is 1 + 1?      2
    1  What is 2 + 2?      4
"""
def answer_questions(dataset:pd.DataFrame, prompt_template:str, answer_col:str, model='gpt4'):
#   print("prompt_template =", prompt_template)
    map_dataframe(dataset, prompt_template=prompt_template, output_col=answer_col, model=model)
    print(dataset)    

# ----------------------------------------

config.doc['answer_questions_multiple_choice'] = """
def answer_questions_multiple_choice(dataset:pd.DataFrame, prompt_template:str, options, answer_col:str, model:str):
Purpose:
    Same as answer_questions, except answers are constrained to options.
    For every row in the dataset, query the model with the instantiated prompt_template, and put answers under a new column called answer_col.
Args:
    dataset (DataFrame): the dataset, containing items (e.g., questions) under a particular column (e.g., 'question')
    prompt_template (str): The template prompt to query model with. The template reference the item column
    options (list(str)): The allowed answer options
    answer_col (str): The DataFrame column to place the answers in
    model (str): The model to query. For now, valid answers are 'gpt4', 'olmo', 'llama', and 'mistral'
Returns:
    DataFrame: The dataset DataFrame updated with the answers. (Note: the dataset Dataframe is destructively updated)
Example:
    dataset = pd.DataFrame([{'question':'Is water wet?'}, {'question':'Can birds fly?'}])
    answer_questions_multiple_choice(dataset, "Answer this: {question}", options=["yes","no"], answer_col='answer', model='olmo')
    print(dataset)
    ->          question answer
    0   Is water wet?    yes
    1  Can birds fly?    yes
"""
def answer_questions_multiple_choice(dataset:pd.DataFrame, prompt_template:str, options, answer_col:str, model='gpt4'):
    map_dataframe_multiple_choice(dataset, prompt_template=prompt_template, options=options, output_col=answer_col, model=model)
    print(dataset)        

# ----------------------------------------

config.doc['score_answers'] = """
def score_answers(dataset:pd.DataFrame, prompt_template:str, score_col='score', score_range=10, model:str='gpt4'):    
Purpose:
    Use model (LM-as-judge) to score a set of answers in dataset. Scores are added to the dataset DataFrame.
    The function queries the model for every row in the data frame with the instantiated prompt_template, 
    and collects the scoring information as an instantiated json_template.
Args:
    dataset (DataFrame): The dataset
    prompt_template (str): Describes how to score individual answers in each row of the dataset
    score_col (str): The column to put the scores in (default 'score').
    score_range (int): The range of scores, e.g., if scores are 0 to 10, then the score_range is 10. This is used for score normalization.
    model (str) (optional): The model to do the scoring. Valid models are 'gpt4', 'o1-mini' and 'o3-mini'. Default is 'gpt4'
Returns:
    DataFrame: The dataset DataFrame updated with the scores in score_col, and also a justification in column {score_col}_justification
Example:
    dataset = pd.DataFrame([{"question":"What is the sum of 34 and 21?","answer":"The sum of 34 and 21 is 55."},
                            {"question":"Add 58 and 36 together.","answer":"Add 58 and 36: 94."}])
    score_answers(dataset, "Score the answer to the following question between 0 (completely wrong) and 10 (completely correct):\nQuestion: {question}\nAnswer: {answer}", score_col='score', score_range=10)
    print(dataset)
                        question                       answer    score                                                   score_justification
0  What is the sum of 34 and 21?  The sum of 34 and 21 is 55. 1.000000  The answer is completely correct. The sum of 34 and 21 is indeed 55.
1        Add 58 and 36 together.           Add 58 and 36: 94. 1.000000                  The answer is completely correct. 58 + 36 equals 94.
"""
def score_answers(dataset:pd.DataFrame, prompt_template:str, score_col='score', score_range=10, model:str=config.LLM_AS_JUDGE):
    score_template_json = f'{{ {score_col}:INTEGER, {score_col}_justification: JUSTIFICATION }}'
    map_dataframe_json(dataframe=dataset, prompt_template=prompt_template, json_template=score_template_json, model=model)
    dataset[score_col] = dataset[score_col]/score_range            ## Normalize the score to be range 0-1
    dataset[score_col] = pd.to_numeric(dataset[score_col]) 	   ## coerce score to be numeric
    print(dataset)
    
### ======================================================================
###	Qualitative interpretation of stats
### ======================================================================


config.doc['spearman_strength'] = """
def spearman_strength(spearman_corr:float):
Purpose:
    Convert a Spearman rank correlation coefficient to a qualitative word, according to this conversion table:
	 .00-.19 very weak
	 .20-.39 weak
	 .40-.59 moderate
	 .60-.79 strong
	 .80-1.0 very strong
Args:
    spearman_corr (float): The Spearman correlation coefficient (range -1 to 1)
Returns:
    One of the five words above, interpreting the number
Example:
    print(spearman_strength(0.54))
-> moderate
"""
def spearman_strength(spearman_corr:float):
    """ Interpretation sourced from: https://www.statstutor.ac.uk/resources/uploaded/spearmans.pdf
	 .00-.20 very weak
	 .20-.40 weak
	 .40-.60 moderate
	 .60-.80 strong
	 .80-1.0 very strong
    """
    abs_corr = abs(spearman_corr)  # Use absolute value to handle both positive and negative correlations
    if abs_corr < 0.2:
        return "very weak"
    elif 0.20 <= abs_corr < 0.4:
        return "weak"
    elif 0.40 <= abs_corr < 0.6:
        return "moderate"
    elif 0.60 <= abs_corr < 0.8:
        return "strong"
    elif 0.80 <= abs_corr <= 1.00:
        return "very strong"
    else:  # Handle cases outside the expected range (optional, but good practice)
        return f"Spearman correlation value {spearman_corr} is out of the expected range [-1, 1]"
    
config.doc['pearson_strength'] = """
def pearson_strength(pearson_corr:float):
Purpose:
    Convert a Pearson correlation coefficient to a qualitative word, according to this conversion table:
	 .00-.30 very weak
	 .30-.50 weak
	 .50-.70 moderate
	 .70-.90 strong
	 .90-1.0 very strong
Args:
    spearman_corr (float): The Spearman correlation coefficient (range -1 to 1)
Returns:
    One of the five words above, interpreting the number
Example:
    print(spearman_strength(0.54))
-> moderate
"""
def pearson_strength(pearson_corr:float):
    """ Interpretation source from https://www.andrews.edu/~calkins/math/edrm611/edrm05.htm:
	 - Correlation coefficients whose magnitude are between 0.9 and 1.0 indicate variables which can be considered very highly correlated. 
	 - Correlation coefficients whose magnitude are between 0.7 and 0.9 indicate variables which can be considered highly correlated. 
	 - Correlation coefficients whose magnitude are between 0.5 and 0.7 indicate variables which can be considered moderately correlated. 
	 - Correlation coefficients whose magnitude are between 0.3 and 0.5 indicate variables which have a low correlation. 
	 - Correlation coefficients whose magnitude are less than 0.3 have little if any (linear) correlation. 
    """
    abs_corr = abs(pearson_corr)

    if abs_corr < 0.3:
        return "very weak"
    elif 0.30 <= abs_corr < 0.5:
        return "weak"
    elif 0.50 <= abs_corr < 0.7:
        return "moderate"
    elif 0.70 <= abs_corr < 0.9:
        return "strong"
    elif 0.90 <= abs_corr <= 1.00:
        return "very strong"
    else:  # Handle cases outside the expected range (optional, but good practice)
        return f"Person correlation value {pearson_corr} is out of the expected range [-1, 1]"

# ======================================================================
#	PRINTING THE DOCUMENTATION (more robust than copy-and-edit)
# ======================================================================

def save_documentation(docfile=config.FUNCTION_DOC_FILE):
    with open(docfile, 'w') as file:
        file.write(get_function_documentation())
    print(f"Documentation written out to {docfile}.")

def get_function_documentation():
#   print("DEBUG: config.doc =", config.doc)
    DIVIDER = "\n----------------------------------------\n"    
    documentation = ("""
USEFUL PYTHON FUNCTIONS
=======================

1. RESEARCH TOOLS
-----------------\n""" +
    config.doc['create_dataset'] + DIVIDER +
    config.doc['answer_questions'] + DIVIDER +
    config.doc['score_answers'] + DIVIDER +
    config.doc['ideate_categories_fn'] + DIVIDER +
    config.doc['examples_in_category'] + """
2. LITERATURE TOOLS
-------------------\n""" +
    config.doc['find_paper_ids'] + DIVIDER +
    config.doc['get_paper_text'] + DIVIDER +
    config.doc['summarize_paper'] + DIVIDER +
    config.doc['ask_paper'] + DIVIDER +                      
    config.doc['get_paper_details'] + """                     
3. STATISTICS
-------------\n""" +
    config.doc['spearman_strength'] + DIVIDER +
    config.doc['pearson_strength'] + """
4. BASIC CALLS TO A LLM
-----------------------\n""" +
    utils_config.doc['call_llm'] + DIVIDER +                    
    utils_config.doc['llm_list'])
    return documentation

# ----------

def get_workflow_documentation():
    with open(config.WORKFLOW_DOC_FILE, 'r') as file:
        return file.read()

# ----------

# we generate PLAN_DOC_FILE dynamically
def get_plan_documentation():
    extract_plan_from_workflow(config.WORKFLOW_DOC_FILE, config.PLAN_DOC_FILE)
    with open(config.PLAN_DOC_FILE, 'r') as file:
        return file.read()
    
# courtesy Gemini                   
def extract_plan_from_workflow(workflow_doc_file=config.WORKFLOW_DOC_FILE, plan_doc_file=config.PLAN_DOC_FILE):
    try:
        with open(workflow_doc_file, 'r') as infile, open(plan_doc_file, 'w') as outfile:
            for line in infile:
                if line.startswith('#'):
                    trimmed_line = line.lstrip('#').lstrip() #remove leading '#' and extra whitespace
                    if trimmed_line == '':
                        outfile.write('\n')		# if ONLY '#', then the terminating '\n' becomes a *leading* whitespace char and is trimmed
                    else:
                        outfile.write(trimmed_line)
    except FileNotFoundError:
        print(f"Error: File '{workflow_doc_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

                   
                
                   
                   

        

    
    
