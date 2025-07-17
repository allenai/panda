
import pandas as pd

"""
def score_categories(dataset:pd.DataFrame, categories:pd.DataFrame, *, data_cat_col:str, score_col:str, highlow:str='high'):
Purpose:
    Compute a score for each category, where score = average of score_col for dataset examples in that category
    Also adds two columns n_covered (number) and f_covered (fraction) to categories, showing how much of the dataset this category covers.
Args:
    dataset (DataFrame): A DataFrame with questions and their category memberships.
    categories (DataFrame): A DataFrame with category information.
    data_cat_col (str): The column of dataset containing category membership information, in the form of a JSON array of
   			  	[{index:<category_index>, score:<score>},...]
                        where <score> is 0-1, showing how much this row is a member of the category with category_index
    score_col (str): The dataset metric to average over, when computing the category score
    highlow (str): If 'high', then a "good" category is one with higher score (metric). If 'low', a "good" category has a lower score.
                   The sign of the returned signal is adjusted using this, so a high signal always means "good".
Returns:
    The categories dataframe, with score statistics added in several new columns:
        score: the average data_metric for dataset examples in this category
        adj_score: An adjusted score, to account for categories with few examples in. The adj_score is the one to pay attention to.
        n_covered: the number of dataset examples in this category
        f_covered: the fraction of dataset examples in this category
        signal: The discriminative-ness of this category, defined as the difference between the adj_score and overall average score in the dataset.

Example:
    dataset = pd.DataFrame([{'question':'1+1?',  'answer': 2,'score':1.0, 'categories':[{'index':0,'score':1},{'index':1,'score':1.0},{'index':2,'score':0.0}]},
			    {'question':'20+20?','answer':40,'score':1.0, 'categories':[{'index':0,'score':1},{'index':1,'score':0.0},{'index':2,'score':1.0}]},
			    {'question':'2+2?',  'answer': 5,'score':0.0, 'categories':[{'index':0,'score':1},{'index':1,'score':1.0},{'index':2,'score':0.0}]}])
    categories = pd.DataFrame([{'title':'everything', 'description':'The entire dataset'},
                               {'title':'Single digit addition','description':'Math problems that involve only adding single digit numbers together'},
                               {'title':'Two digit addition','description':'Math problems that involve only adding two digit numbers together'}])
    score_categories(dataset, categories, data_cat_col='categories', score_col='score')
    print(categories.to_csv(sep='\t'))
	title			description								score n_covered	f_covered adj_score  signal  
0	everything		The entire dataset							0.66	3	1.0       0.66       0.000
1	Single digit addition	Math problems that involve only adding single digit numbers together	0.5	2	0.66      0.63       -0.027
2	Two digit addition	Math problems that involve only adding two digit numbers together	1.0	1	0.33      0.69       0.030
"""
def score_categories(dataset:pd.DataFrame, categories:pd.DataFrame, data_cat_col:str, score_col:str, highlow:str='high'):

    if data_cat_col not in dataset.columns:
        # Helpful message to help Panda repair itself
        raise Exception(f"You can't score categories until you have first placed the examples in {dataset} into those categories!\nPlease call place_items_in_categories({dataset}, {categories}, ...) first.")
    cat_score_col = 'score'	# hardwire this I think

    for index, category_row in categories.iterrows():
        category_scores = []
        for _, row in dataset.iterrows():
            for category in row[data_cat_col]:
                if category['index'] == index and category['score'] > 0.5:
                    category_scores.append(row[score_col])

#       average_score = sum(category_scores) / len(category_scores) if category_scores else '?'        	# '?' leads to a dtype warning
        average_score = sum(category_scores) / len(category_scores) if category_scores else 0
        categories.at[index, cat_score_col] = average_score
        categories.at[index, 'n_covered'] = int(len(category_scores))
        if index == 0:											# assume index 0 is the first row processed
            overall_n_covered = len(category_scores)			
        categories.at[category_row.name, 'f_covered'] = len(category_scores) / overall_n_covered        

    categories['n_covered'] =  categories['n_covered'].astype(int)		# for some reason they are floats

    # NEW: Fold this into score_categories
    categories = add_signal(categories, cat_score_col=cat_score_col, highlow=highlow)
    return categories

### ----------------------------------------

"""
U: Now add a 'Adjusted Score' computed from the 'Score' via the following formula:

    adjusted_score_basis = 10
    adjusted_score = ((score*n_covered) + 1) / (n_covered + adjusted_score_basis)

Now add another column to question_categories containing the absolute difference between the 'Adjusted Score' and the overall average score, contained in the 'Score' of row 0 of question_categories.
"""
ADJUSTED_SCORE_BASIS = 10

def add_signal(categories, cat_score_col:str=None, cat_adj_score_col:str=None, cat_signal_col:str=None, highlow:str='high'):
    """Adds columns 'adj_score' and 'signal' to the categories DataFrame.
    Args:
    categories: A DataFrame containing categories and their scores.
    Returns:
    The modified DataFrame.
    """
    if cat_score_col is None:
        raise ValueError("Error! You must provide cat_score_col=... to add_signal!")
    cat_signal_col = "signal" if cat_signal_col is None else cat_signal_col
    cat_adj_score_col = "adj_" + cat_score_col if cat_adj_score_col is None else cat_adj_score_col	  
    overall_average_score = categories.loc[0, cat_score_col]		# index 0 is "everything"
    signal_sign = -1 if highlow == 'low' else +1                         # 'low' means lower values are better

    def calculate_signal(row):
        score = row[cat_score_col]
        n_covered = row['n_covered']
        if score == '?':
            return '?', 0, 0
        else:
            # [not used] signal = abs(score - overall_average_score)		# overall_average_score is global to add_signal's scope
            adjusted_score = ((score * n_covered) + (overall_average_score * ADJUSTED_SCORE_BASIS)) / (n_covered + ADJUSTED_SCORE_BASIS)
            adjusted_signal = (adjusted_score - overall_average_score) * signal_sign       
            return adjusted_score, adjusted_signal

    categories[[cat_adj_score_col, cat_signal_col]] = categories.apply(calculate_signal, axis=1, result_type='expand')
#   print("DEBUG: categories['signal'] =", categories['signal'])
    categories = categories[(categories['signal'] > 0.000001) | (categories.index == 0)]   # remove rows with a zero or negative signal (but keep "everything" row 0)
#   print("DEBUG: new categories table =", categories)
    return categories  



