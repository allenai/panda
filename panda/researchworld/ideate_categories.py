
import pandas as pd

from panda.utils import llm_list_json
from .score_categories import score_categories
from .categorize_items import place_items_in_categories
from . import config

MAX_N_SAMPLE = 5         # for ideating good and bad categories

# global, to track created categories
created_categories = []

config.doc['ideate_categories_fn'] = """
def ideate_categories(dataset:DataFrame, item_col:str='question', score_col:str='score', highlow:str='high', n=None):
Purpose:
    Given a dataset of items, and a metric (e.g., score), speculate on categories that cover items with high values for that metric, but not items with low values.
    Essentially, each category should partition the dataset according to metric.
Args:
    dataset (DataFrame): A DataFrame of objects (e.g., questions)
    item_col (str): The column of dataset listing the objects
    score_col (str): The dataset metric to use for partitioning objects
    highlow (str): If 'high', then categories should cover objects with high metric values. If 'low', they should cover objects with low metric values.
    n (int) (optional): The number of categories to ideate
Returns:
    categories (DataFrame): A new DataFrame containing the ideated categories, with the following fields (one per category):
        title: The name of the ideated category
        description: A description of the category
        score: the average data_metric just for dataset examples in this category
        adj_score: An adjusted score, to account for categories with few examples in. The adj_score is the one to use when reasoning about the category.
        n_covered: the number of dataset examples in this category
        f_covered: the fraction of dataset examples in this category
        signal: The OVERALL QUALITY, or discriminative-ness, of this category, defined as the difference between the adj_score and overall average score in the dataset.
Notes: 
    - The categories are returned sorted, those with the highest (lowest) signal first, except the first row (iloc[0], loc[0]) representing the special category "everything".
      Thus you can select the best (highest signal) category via categories.iloc[1].
    - If there are more than ~30 items in the dataset, scoring is just done with a random sample from that dataset
    - The row with index 0 contains the special category "Everything", covering the entire dataset (n_covered = the full random sample size used for scoring)

Example:
    dataset = pd.DataFrame([{"question":"1+1?","answer":2,"score":1.0},
                            {"question":"20+20?","answer":43,"score":0.0},
                            {"question":"23+33?","answer":123,"score":0.0},
                            {"question":"2+2?","answer":4,"score":1.0}])
    difficult_categories = ideate_categories(dataset, item_col='question', score_col='score', highlow='low', n=3)          # difficult categories have LOW score
    print(difficult_categories)   # categories of "difficult" (low-scoring) questions
                                     title                                                            description    score  n_covered  f_covered  adj_score    signal
    0                           everything                                                     The entire dataset 0.500000          4   1.000000   0.500000 -0.000000
    1          Addition of multiples of 20  Questions involving the addition of numbers that are multiples of 20. 0.000000          1   0.250000   0.454545  0.045455
    2       Addition resulting in above 40                            Questions where the sum is greater than 40. 0.000000          1   0.250000   0.454545  0.045455
    3  Addition with both addends above 20          Questions where both numbers being added are greater than 20. 0.000000          1   0.250000   0.454545  0.045455
Example:
    easy_categories = ideate_categories(dataset, item_col='question', score_col='score', highlow='high', n=3)
    print(easy_categories)
->                 title                                                      description    score  n_covered  f_covered  adj_score   signal
    0              everything                                               The entire dataset 0.500000          4   1.000000   0.500000 0.000000
    1  Single Digit Additions  Addition problems where all numbers involved are single digits. 1.000000          2   0.500000   0.583333 0.083333
    easiest_category = easy_categories.iloc[1]
"""
def ideate_categories(dataset, item_col='question', score_col='score', highlow='high', n=None):
    global created_categories
    # 1. Sample 3 items with a low score, and 3 with a high score
#   worst3 = dataset[dataset[score_col] < 0.5].nsmallest(3, score_col)	# must get item wrong - makes too many assumptions though
#   best3  = dataset[dataset[score_col] > 0.5].nlargest( 3, score_col)	# must get item right

    n_sample = min(MAX_N_SAMPLE,round(len(dataset)/2))
    top3 = dataset.nlargest( n_sample, score_col)
    bot3 = dataset.nsmallest(n_sample, score_col)
    average_score = pd.concat([top3,bot3])[score_col].mean()
    top3_filtered = top3[top3[score_col] > average_score]
    bot3_filtered = bot3[bot3[score_col] <= average_score]    

    if highlow == 'high':
        best3  = top3_filtered
        worst3 = bot3_filtered
        lowhigh = 'low'
    elif highlow == 'low':
        best3  = bot3_filtered
        worst3 = top3_filtered
        lowhigh = 'high'
    else:
        raise Exception(f"Error! ideate_categories(): highlow='{highlow}', but should be 'high' or 'low'!")

    # 2. Format them out nicely as strings
    formatted_best3  = "\n".join(f"Q{row.name}: {row[item_col]} (score {row[score_col]})" for index, row in  best3.iterrows())
    formatted_worst3 = "\n".join(f"Q{row.name}: {row[item_col]} (score {row[score_col]})" for index, row in worst3.iterrows())

    # 3. Ask GPT for categories
    n_cats = str(n) if n else "some"
    prompt = f"""----------------------------------------------------------------------
Here are {len(best3)} {item_col}s with {highlow} {score_col}s:
----------------------------------------------------------------------
{formatted_best3}
----------------------------------------------------------------------
Here are {len(worst3)} {item_col}s with {lowhigh} {score_col}s:
----------------------------------------------------------------------
{formatted_worst3}
----------------------------------------------------------------------
List {n_cats} possible categories that cover the {item_col}s with {highlow} {score_col}s, but do not cover the {item_col}s with {lowhigh} {score_col}s."""
    difficult_item_category_list = llm_list_json(prompt, "{'title':CATEGORY_TITLE, 'description':CATEGORY_DESCRIPTION}", n=n)

#   print("DEBUG: ideation prompt =", prompt)
    # 4. Create an "everything" category for index 0
    everything_category = {'title':"everything", 'description':"The entire dataset"}

    # 5. Place categories in a DataFrame
    categories = pd.DataFrame([everything_category] + difficult_item_category_list)	# "everything" will have index 0
    data_cat_col = get_unique_column_name(dataset, base_name='categories')
    											# allows us to use different metrics on the same dataset
    place_items_in_categories(dataset, categories, item_col=item_col, data_cat_col=data_cat_col, cat_title_col='title', cat_description_col='description')
    categories = score_categories(dataset, categories, data_cat_col=data_cat_col, score_col=score_col, highlow=highlow)
    categories['data_cat_col'] = data_cat_col					# squirrel away the data_cat_col name in (every row of) categories, to link categories to dataset

    # 6. Sort the final result, with the highest signal categories first
    categories_sorted = pd.concat([
        categories.loc[[0]],  # Keep the first row unchanged
        categories.iloc[1:].sort_values(by='signal', ascending=False)  # Sort all other rows
    ])
    
#    row_0 = categories.loc[0]
#    categories_sorted = categories.loc[1:].sort_values('signal', ascending=False)
#    final_categories = pd.concat([row_0, categories_sorted])

    print(categories_sorted)
    created_categories += [categories_sorted]
    return categories_sorted

# ------------------------------

# Function to find the next available column name
# returns 'categories', unless the column already exists, in which case it returns 'categories1', etc.
def get_unique_column_name(df, base_name='categories'):
    new_name = base_name
    counter = 1
    while new_name in df.columns:
        new_name = f"{base_name}{counter}"
        counter += 1
    return new_name

# ----------------------------------------

config.doc['examples_in_category'] = """
def examples_in_category(dataset:pd.DataFrame, category_row:pd.Series, score_col='score', highlow='high', n=9999):
Purpose: 
    Find examples (rows in dataset) of a given category (a row from a categories DataFrame)
Args:
    dataset (DataFrame): A dataset of items (QA pairs, etc.)
    category_row (Series): A row from a categories DataFrame, representing a particular ideated category
    score_col (str): The column in dataset containing the score (metric) by which dataset items are being evaluated
    highlow (str): one of 'high' or 'low', indicating if the category aims to select items with unusually high or low score
    n (int) (optional): the number of dataset examples to return. (default = return all examples in category)
Returns:
    DataFrame: A subset of n rows in dataset, containing dataset items in the target category. The ones with
               highest (lowest) score_col are selected first.
Example:
    dataset = pd.DataFrame([{"question":"1+1?","answer":2,"score":1.0},
                            {"question":"20+20?","answer":43,"score":0.0},
                            {"question":"23+33?","answer":123,"score":0.0},
                            {"question":"2+2?","answer":4,"score":1.0}])
    easy_categories = ideate_categories(dataset, item_col='question', score_col='score', highlow='high', n=3)
    print(easy_categories)
->                 title                                                      description    score  n_covered  f_covered  adj_score   signal
    0              everything                                               The entire dataset 0.500000          4   1.000000   0.500000 0.000000
    1  Single Digit Additions  Addition problems where all numbers involved are single digits. 1.000000          2   0.500000   0.583333 0.083333
    easiest_category = easy_categories.iloc[1]
    print(examples_in_category(dataset, easiest_category, score_col='score', highlow='high', n=1))
->    question  answer    score 
    0     1+1?       2 1.000000 
"""
def examples_in_category(dataset:pd.DataFrame, category_row:pd.Series, score_col='score', highlow='high', n=9999):

    cat_index = category_row.name
    ascending = False if highlow == 'high' else True
    if 'data_cat_col' in category_row.index:
        data_cat_col = category_row['data_cat_col']
    else:
        raise ValueError("Error! The category_row is missing a 'data_cat_col' pointer back to the categories column in the dataset DataFrame!")

    def local_is_in_category(row, cat_index):
        for category in row[data_cat_col]:
#           print("category =", category)          # e.g.,  {'index': 0, 'score': 1}
            if category['index'] == cat_index and category['score'] > 0.5:
#               print("-> true!")
                return True
#       print("-> false")            
        return False

#   dataset_in_category = dataset[local_is_in_category(dataset[data_cat_col],cat_index)]
#   dataset_in_category = dataset[lambda dataset: local_is_in_category(dataset[data_cat_col], cat_index)]
    dataset_in_category = dataset[dataset.apply(local_is_in_category, axis=1, args=(cat_index,))]

    return dataset_in_category.sort_values(score_col, ascending=ascending).head(n)

