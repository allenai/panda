
import pandas as pd

from .ask_llm import call_llm, call_llm_json, call_llm_multiple_choice
from . import config		# for DEFAULT_GPT4_MODEL
from panda.panda_agent import config as agent_config

LIST_BATCH_SIZE = 10

config.doc['llm_list'] = """
def llm_list(prompt:str, model:str):
Purpose:
    Get a list of string answers from an LLM in a single call. This function queries the LLM with the prompt, extracts a list of answers, and returns them as a list.
Args:
    prompt (str): The prompt to be sent to GPT. The prompt should specify the number of items to return. 
                  It is good practice to include an example of the item to return in the prompt.
    model (str): The LLM to call. Currently must be one of 'gpt4' or 'o1-mini'.
Returns:
    list: A list of items (strings)
Example:
    print(llm_list("Generate 3 test questions for a children's quiz that test simple two-digit addition, e.g., 'What is 23 + 34?'"))
 -> ['What is 34 + 21?', 'How much is 47 + 15?', 'Add 58 and 36 together.']
Example:
    print(llm_list("Tell me some countries."))
 -> ['China', 'India', 'United States', 'Indonesia', 'Pakistan']
"""
def llm_list(prompt:str, temperature=0, quiet=True, n=None, model=agent_config.PANDA_LLM):
    element_json = f'{{"number":INTEGER, "item":ITEM}}'
    response = llm_list_json(prompt, element_json, temperature=temperature, quiet=quiet, n=n, model=model)
    result = []
    for item_data in response:
        try:
            result.append(item_data['item'])
        except KeyError:
            print(f"WARNING! llm_list: No pair with key 'item' found in dict element {item_data}....Ignoring it and continuing...")
    return result            

### ----------

"""
def llm_list_json(prompt:str, json_template:str, model:str):
Purpose:
    Get a list of JSON answers from an LLM in a single call. This function queries LLM with the prompt, extracts a list of answers as JSON objects, and returns them as a JSON array.
Args:
    prompt (str): The prompt to be sent to GPT. The prompt should specify the number of items required.
    json_template (str): The template JSON to return for each answer
    model (str): The LLM to call. Currently must be one of 'gpt4' or 'o1-mini'.
Returns:
    JSON array: A list of JSON objects, formatted following the json_template template.
Example:
    print(llm_list_json("Give me two famous names", '{"first_name",FIRST_NAME, "surname":SURNAME}'))
 -> [{'first_name': 'Albert', 'surname': 'Einstein'}, {'first_name': 'Marie', 'surname': 'Curie'}]
Example (no number of items provided):
    print(llm_list_json("List some famous people", '{"name":NAME}'))         
 -> [{'name': 'Albert Einstein'},
     {'name': 'Marie Curie'},
     {'name': 'Martin Luther King Jr.'},
     {'name': 'William Shakespeare'}]

"""
def llm_list_json(prompt, json_template:str, temperature=0, quiet=True, n=None, model=agent_config.PANDA_LLM):
#   print("DEBUG: n=", n, "prompt =", prompt)
    if not n:
        n_json,_ = call_llm_json(f'The following request asks for a number of items. Return JUST that number, as an integer, in the JSON format {{"n":INTEGER}}. If you can\'t find the number, return the integer 0. Here is the request: "{prompt}"')
        n = n_json['n']
        if n != 0:			# note you can just ask for "some" items
            print(f"DEBUG: Found that {n} items are requested...")
    struct_prompt = f'\nReturn your answer as a compact JSON object, formatted as a single line with no unnecessary spaces or newlines, in the following structure:\n   {{"answer": [{json_template}, {json_template}, ...]}}'
    if n > LIST_BATCH_SIZE:
        full_prompt = prompt + f"\nTo make this manageable, let's generate the items in batches of {LIST_BATCH_SIZE}." + struct_prompt + f"\nGo ahead and generate the first {LIST_BATCH_SIZE} items."
    else:
        full_prompt = prompt + struct_prompt

    dialog = []
    dialog += [full_prompt]
    if not quiet:
        print("SYSTEM: ", full_prompt)
#   print("dialog =", dialog)
    response, response_str = call_llm_json(dialog, temperature=temperature)
    if not quiet:
        print("GPT: ", response_str)
    dialog += [response_str]

    try:
        item_list = response.get('answer', [])  # Get the list of questions, or an empty list if 'answer' key is not found
    except KeyError:
        print("Yikes! No 'answer' field in result from GPT.. no values found...")
        ite_list = []  # Handle the case where the 'answer' key is not found

    remaining = n - LIST_BATCH_SIZE if n else 0
    while remaining > 0:
        print_progress()
        next_batch_size = min(remaining, LIST_BATCH_SIZE)  # Calculate batch size (can be smaller than LIST_BATCH_SIZE for the last batch)
        try:
            another = "another" if remaining > LIST_BATCH_SIZE else "the last"
            prompt = f"Now generate {another} {next_batch_size} items."
            dialog += [prompt]
#           print("dialog =", dialog)
            if not quiet:
                print("SYSTEM: ", prompt)
            response, response_str = call_llm_json(dialog, temperature=temperature)
            if not quiet:
                print("GPT: ", response_str)
            dialog += [response_str]
            batch_items = response.get('answer', [])
            if not batch_items: # Handle empty responses within a batch
                print("Warning: GPT returned an empty 'answer' list in a batch. Retrying the batch...")
                continue # Retry the current batch
            item_list.extend(batch_items)
            remaining -= len(batch_items) # Decrement remaining by the actual number of received items

        except (json.JSONDecodeError, KeyError, AttributeError) as e: # Catch JSON errors and other potential errors
            print(f"Error processing GPT response: {e}.  Response was: {response_str}")  # Print response string for debugging
            print("Yikes! Issues with JSON or 'answer' field...returning accumulated values so far...")
            return item_list # Return what we have so far, even if incomplete
            # Consider: break here instead of return if you want to stop completely on errors

    return item_list
        
### ----------------------------------------------------------------------

"""
def map_dataframe(dataframe:pd.DataFrame, prompt_template:str, output_col:str, model=agent_config.PANDA_LLM):
Purpose:
    For every row in dataframe, query the model with the instantiated prompt_template, and put answers in the DataFrame column called output_col.
Args:
    dataframe (DataFrame): input data
    prompt_template (str): The template prompt to query model with
    output_col (str): The DataFrame column to place the answers in
    model (str): The LLM to call. Currently must be one of 'gpt4' or 'o1-mini'.
Returns:
    DataFrame: The input dataframe updated with the answers. (Note: the input dataframe is destructively updated)
Example:
    x = pd.DataFrame([{'question':'What is 1 + 1?'}, {'question':'What is 2 + 2?'}])
    map_dataframe(x, "Answer this question: {question}", 'answer', model='llama')      # x is destructively updated
    print(x)
             question answer
    0  What is 1 + 1?      2
    1  What is 2 + 2?      4

[1] Can't have this function call map_dataframe_json internally as we need to allow non-JSON answers from model='llama'
"""
def map_dataframe(dataframe:pd.DataFrame, prompt_template:str, output_col:str, model=agent_config.PANDA_LLM, quiet=True):

    responses = []
    for row_dict in dataframe.to_dict('records'):
        print_progress()
        try:
            prompt = prompt_template.format(**row_dict)
        except Exception as e:
            raise KeyError(f"GPT exception {e}. prompt_template might be referring to a column that's not in the dataframe?")
        responses.append(call_llm(prompt, model=model, quiet=quiet))    # [1]        

    dataframe[output_col] = responses
    return dataframe        

### ----------------------------------------------------------------------

"""
def map_datafram_multiple_choice(dataframe:pd.DataFrame, prompt_template:str, options, output_col:str, model=agent_config.PANDA_LLM):
Purpose:
    Same as map_dataframe, except the responses are constained to be one of options.
    For every row in dataframe, query the model with the instantiated prompt_template, and put answers in the DataFrame column called output_col.
Args:
    dataframe (DataFrame): input data
    prompt_template (str): The template prompt to query model with
    options (list(str)): The allowed answer options
    output_col (str): The DataFrame column to place the answers in
    model (str): The model to query.
Returns:
    DataFrame: The input dataframe updated with the answers. (Note: the input dataframe is destructively updated)
Notes:
Example:
    x = pd.DataFrame([{'question':'Is water wet?'}, {'question':'Can birds fly?'}])
    map_dataframe_multiple_choice(x, "Answer this question: {question}", ["yes","no"], 'answer', model='llama')      # x is destructively updated
    print(x)
             question answer
    0  What is 1 + 1?      2
    1  What is 2 + 2?      4

[1] Can't have this function call map_dataframe_json internally as we need to allow non-JSON answers from model='llama'
"""
def map_dataframe_multiple_choice(dataframe:pd.DataFrame, prompt_template:str, options, output_col:str, model=agent_config.PANDA_LLM, quiet=True):

    responses = []
    for row_dict in dataframe.to_dict('records'):
        print_progress()
        try:
            prompt = prompt_template.format(**row_dict)
        except Exception as e:
            raise KeyError(f"GPT exception {e}. prompt_template might be referring to a column that's not in the dataframe?")
        responses.append(call_llm_multiple_choice(prompt, options, model=model, quiet=quiet))    # [1]        

    dataframe[output_col] = responses
    return dataframe        

### ======================================================================
"""
def map_dataframe_json(dataframe:pd.DataFrame, prompt_template:str, json_template:str):
Purpose:
    For every row in dataframe, query the model with the instantiated prompt_template, and collect the answer as an instantiated json_template.
    Add each answer element (key:value) in that answer to the dataframe in the column named key.
Args:
    dataframe (DataFrame): input data
    prompt_template (str): The template prompt to query model with
    json_template (str): The template JSON to collect GPT's answer in 
Returns:
    DataFrame: The input dataframe updated with the answers. (Note: the input dataframe is destructively updated)
Example:
dataset = pd.DataFrame(
  [{"question":"What is the sum of 34 and 21?","answer":"The sum of 34 and 21 is 55."},
   {"question":"Add 58 and 36 together.","answer":"Add 58 and 36: 94."}]
map_dataframe_json(dataset, "Score the answer to the following question between 0 (completely wrong) and 10 (completely correct), and give a justification:\nQuestion: {question}\nAnswer: {answer}", '{"score10": INTEGER, "justification": JUSTIFICATION}')
print(dataset.to_csv(sep='\t'))
	question	answer	score10	justification
0	What is the sum of 34 and 21?	The sum of 34 and 21 is 55.	10	The answer provided is completely correct. The sum of 34 and 21 is indeed 55.
1	Add 58 and 36 together.	Add 58 and 36: 94.	10	The answer provided is completely correct. When you add 58 and 36 together, the sum is indeed 94.
"""
def map_dataframe_json(dataframe:pd.DataFrame, prompt_template:str, json_template:str, quiet=True, model=agent_config.PANDA_LLM):
    prompt_extra = f"\nReturn your answer as a JSON object with the following structure: {json_template}"            
    responses = []
    for row_dict in dataframe.to_dict('records'):
        print_progress()
        try:
            prompt = prompt_template.format(**row_dict)
        except Exception as e:
            raise KeyError(f"GPT exception {e}. prompt_template might be referring to a column that's not in the dataframe?")
        response_json,_ = call_llm_json(prompt+prompt_extra, model=model)
        responses.append(response_json)
    return add_list_of_dicts_to_df(dataframe, responses)

## sub-utility    
def add_list_of_dicts_to_df(df, list_of_dicts):
  """
  Adds the data from a list of dictionaries to a DataFrame.
  Args:
    df: The input DataFrame.
    list_of_dicts: A list of dictionaries, where keys may or may not 
                   correspond to existing columns in the DataFrame.
  Returns:
    The updated DataFrame.
  """
  if len(df) != len(list_of_dicts):
    raise ValueError("Length of DataFrame and list of entries to add are different! (should be the same).")

  for index, data in enumerate(list_of_dicts):
    for key, value in data.items():
      if key not in df.columns:
        df[key] = pd.NA  # Create the new column with missing values 
      df.at[index, key] = value 

  return df

"""
# Example usage
x = pd.DataFrame([{"id":1,"name":"fred"},{"id":2,"name":"Joe"},{"id":3,"name":"Mike"}])
y = [{'col1': 10, 'col2': 'a'}, {'col1': 20, 'col2': 'b'}, {'col1': 30, 'col2': 'c'}]

updated_x = add_list_of_dicts_to_df(x, y)
print(updated_x)    
   col1 col2
0    10    a
1    20    b
2    30    c
"""

def print_progress():
    print(".", end="")	
#   print_to_user(".", end="")		# urgh, circular import - need to fix

    
