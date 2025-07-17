
import pandas as pd
from string import Template

from panda.utils import call_llm_json

MAX_ITEMS_TO_CATEGORIZE = 30

### ======================================================================
###	GENERAL VERSION OF CATEGORIZE_QUESTIONS
### ======================================================================

# place_items_in_categories(dataset, 'question', 'categories', categories, 'title', 'description')	# e.g., dataset[1,'categories'] = {{cid:1, score:0.1}, {cid:2, score:1.0}, ...}


"""
def place_items_in_categories(dataset:pd.DataFrame, categories:pd.DataFrame, *, item_col:str, data_cat_col:str, cat_title_col:str, cat_description_col:str):
Purpose: 
    Ask GPT how well objects under item_col in dataset are members of categories under category_description_col in the categories DataFrame.
    Store the results as a JSON array of {'index':cat_index,'score':cat_membership_score} pairs under the category_membership_col in dataset. 
Args:
    dataset (DataFrame): A DataFrame of objects (e.g., questions)
    item_col (str): The column of dataset listing the objects
    data_cat_col (str): The column of dataset storing the JSON arrays that list each object's membership of different categories
    categories (DataFrame): A DataFrame of categories
    cat_title_col (str): The column of categories providing the title of each category
    cat_description_col (str): The column of categories providing the description of each category
Returns:
    The updated dataset DataFrame with an additional data_cat_col listing how well much each object belongs to each category in categories.
Example:
    dataset = pd.DataFrame([{'question':'1+1?'},{'question':'20+20?'}])
    categories = pd.DataFrame([{'title':'everything', 'description':'The entire dataset'},
                               {'title':'Single digit addition','description':'Math problems that involve only adding single digit numbers together'},
                               {'title':'Two digit addition','description':'Math problems that involve only adding two digit numbers together'}])
    place_items_in_categories(dataset, categories, item_col='question', data_cat_col='categories')
    print(dataset.to_csv(sep='\t'))
	question	categories
0	1+1?	[{'index':0,'score':1},{'index':1,'score':1.0},{'index':2,'score':0.0}]
1	20+20?	[{'index':0,'score':1},{'index':1,'score':0.0},{'index':2,'score':1.0}]
"""
def place_items_in_categories(dataset:pd.DataFrame, categories:pd.DataFrame, item_col:str='question', data_cat_col:str='categories',
                              cat_title_col:str='title', cat_description_col:str='description', quiet=True):
#    print(dataset.to_csv(sep='\t'))
#    print(categories.to_csv(sep='\t'))    
    if data_cat_col not in dataset.columns:    # Make sure a data_cat_col column exists
        dataset[data_cat_col] = [[] for _ in range(len(dataset))]  # Initialize with empty list for each row        

    if len(dataset) > MAX_ITEMS_TO_CATEGORIZE:
        print(f"[ Debug: More than {MAX_ITEMS_TO_CATEGORIZE} items ({len(dataset)}) in dataset - just categorizing a sample of {MAX_ITEMS_TO_CATEGORIZE}... ]")
        sample_size = min(MAX_ITEMS_TO_CATEGORIZE,len(dataset))
        dataset_sample = dataset.sample(n=sample_size, random_state=42) 
    else:
        dataset_sample = dataset
    for index, row in dataset_sample.iterrows():
        print(index, end="")        
        question = row[item_col]
        existing_categories = row[data_cat_col]

        for cat_index, cat_row in categories.iterrows():
            print(".", end="")
            title = cat_row[cat_title_col]
            description = cat_row[cat_description_col]

            # Check if the category already exists for this question
            if not any(cat['index'] == cat_index for cat in existing_categories):
                score = is_in_category(question, title, description, quiet=quiet)		# could do if COD==0 then score==1 here
                existing_categories.append({'index': cat_index, 'score': score})

        dataset.at[index, data_cat_col] = existing_categories

    return dataset

### ======================================================================

"""
def is_in_category(statement:str, cat_title:str, cat_description:str):
    Purpose:
        Score how well the statement fits the category description cat_description (range 0-1)
    Args:
        statement (str): The statement to categorize (e.g., a question, a scenario description)
        cat_title (str): The title of the category
        cat_description (str): The description of the category
    Returns:
        float: A number (0-1) reflecting how well the statement fits the category
    Example:
        print(is_in_category("What is 1 + 1?", "addition", "Questions involving simple addition")
        -> 1.0
"""
def is_in_category(statement:str, cat_title:str, cat_description:str, quiet=True):

    if cat_title.lower() == "everything":
        return 1

    # Substitute strings in the define dataset prompt template
    template = Template(CATEGORY_SCORE_PROMPT_TEMPLATE)
    prompt = template.substitute(
        CATEGORY = cat_description,
        STATEMENT = statement)
    answer, answer_str = call_llm_json(prompt)
    if not quiet:
        print("DEBUG: is_in_category: answer =", answer)
    score = answer['score']

    if not quiet:
        print(f"-> is_in_category(\"{statement}\", \"{cat_title}\", \"{cat_description}\")")
        print(f"<- {score}")

    if score == "?":
        return 0.5
    else:
        try:
            return float(score) / 10
        except ValueError:
            print("Invalid input: Answer must be a number or '?'")
            return None  # Or handle the error differently, e.g., raise an exception    
        
### ----------------------------------------------------------------------

# Generalize beyond 'questions' 
CATEGORY_SCORE_PROMPT_TEMPLATE = """
Given a statement (e.g., a question, a scenario description, an object description), and a general category, score how well that statement is a member of that category.
Return a number between 0 (the statement definitely does not fit the category) and 10 (the statement definitely is a member of the category). 
If you are completely unsure, please return a question mark "?". 
For example, if the statement is a question "What is 1 + 1?", and the category is "Questions involving simple addition", then the score would be 10, because the question is clearly a member of that category.

Let's do this now for the following statement and category:
Statement: ${STATEMENT}
Category: ${CATEGORY}

How well do you think this statement fit that category?
Please give a number between 0 (definitely does not fit) and 10 (definitely is a member of this category). If you are completely unsure, please return a question mark "?". 
Please return the answer in a JSON structure of the form   {"score": SCORE}.
Some examples of the style of JSON to return are: {"score": "10"}, {"score": "3"}, or {"score": "?"}.
"""

'''    
CATEGORY_SCORE_PROMPT_TEMPLATE = """
Now: Given a question (e.g., "What is 1 + 1?"), and a category (e.g., "Questions that are simple additions"), I'm wanting to know whether that question is a member of that category or not. Please return a number between 0 (the question definitely does not fit the category) and 10 (the question definitely is a member of the category). If you are completely unsure, please return a question mark "?".  In this example, the score would be 10, as the question "What is 1 + 1?" is clearly a "Question that is a simple addition".

Let's do this now for a question designed to help assess: ${TOPIC}
Question: ${QUESTION}
Category: ${CATEGORY}

How well do you think this question fit that category?
Please give a number between 0 (definitely does not fit) and 10 (definitely is a member of this category). If you are completely unsure, please return a question mark "?". 
Please return the answer in a JSON structure of the form   {"score": SCORE}.
Some examples of the style of JSON to return are: {"score": "10"}, {"score": "3"}, or {"score": "?"}.
"""
'''

    
