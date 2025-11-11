
N_ILLUSTRATIVE_EXAMPLES = 3

### ======================================================================
###		COMPLEX FORMATTING!
### ======================================================================

"""
def categories_table(categories:DataFrame, cat_title_col:str, cat_description_col:str):
Purpose:
    Returns the categories table (including a legend) in HTML format to the console, so it can be later copied into a report.
Args:
    categories (DataFrame): A DataFrame with category information
    cat_score_col (str): The categories column containing the overall category score
    cat_title_col (str): The categories column providing the title of each category
    cat_description_col (str): The categories column providing the description of each category
Returns:
    table (str): The categories table in HTML format, as a string
Example:
    categories = pd.DataFrame([{"title":"everything","description":"The entire dataset","score":0.6666666667,"n_covered":3,"f_covered":1.0,"adj_score":0.6666666667,"signal":0.0},
                               {"title":"Single digit addition","description":"Math problems that involve only adding single digit numbers together",
                                "score":0.5,"n_covered":2,"f_covered":0.6666666667,"adj_score":0.6388888889,"signal":0.0277777778},
                               {"title":"Two digit addition","description":"Math problems that involve only adding two digit numbers together",
                                "score":1.0,"n_covered":1,"f_covered":0.3333333333,"adj_score":0.696969697,"signal":0.0303030303}])
    table = categories_table(categories, cat_score_col='score', cat_title_col='title', cat_description_col='description')
    print(table)
    <p>
        <ul>
          <li><b>CID:</b> The ID of the category
          <li><b>Cov#:</b> The total number of items in this category
          <li><b>Cov%:</b> The fraction of items in this category
          <li><b>score:</b> The average score of Llama for items in this category
          <li><b>adj.score:</b> The adjusted (expected) score for new items, using the Laplace continuation formula
          <li><b>Signal:</b> The "interestingness" of the category, taken as the difference between the (adjusted) category score and overall score. A high signal indicates Llama did unusually well or poorly in this category.
          <li><b><font color=green>Green Categories:</font></b> Llama's score for these categories was greater than average
          <li><b><font color=red>Red Categories:</font></b> Llama's score for these categories was lower than average	
        </ul>
        <p>
    <table style="border:1px solid black;">
    <tr><th>CID</th><th>cov#</th><th>cov%</th><th>score</th><th>adj.score</th><th>Signal</th><th>Category Title: Category Description</th></tr>
    <tr><td></td><td><i>3</i></td><td><i>100%</i></td><td><i>67%</i></td><td><i>67%</i></td><td><i>0</i></td><td><i>everything: The entire dataset</i></td></tr>
    <tr><td>2</td><td>1</td><td>33%</td><td>100%</td><td>70%</td><td>+3.0%</td><td><b><font color=green>Two digit addition:</font></b> Math problems that involve only adding two digit numbers together</td></tr>
    <tr><td>1</td><td>2</td><td>67%</td><td>50%</td><td>64%</td><td>-2.8%</td><td><b><font color=red>Single digit addition:</font></b> Math problems that involve only adding single digit numbers together</td></tr>
    </table>
"""
def categories_table(categories, cat_score_col:str='score', cat_adj_score_col:str='adj_score', cat_signal_col:str='signal', cat_title_col:str='title',
                     cat_description_col:str='description', format='html', tab='\t'):
    table = categories_table_only(categories, cat_score_col=cat_score_col, cat_adj_score_col=cat_adj_score_col, cat_signal_col=cat_signal_col, \
                                  cat_title_col=cat_title_col, cat_description_col=cat_description_col, format=format, tab=tab)
    return categories_table_legend(format) + table

# ----------------------------------------------------------------------

def categories_table_legend(format='html'):
    if format == 'html':
        return HTML_LEGEND
    elif format == 'txt':
        return TXT_LEGEND
    else:
        raise Exception(f"Unrecognized format='{format}' in categories_table_with_legend!")

HTML_LEGEND = """<p>
    <ul>
      <li><b>CID:</b> The ID of the category
      <li><b>Cov#:</b> The total number of items in this category
      <li><b>Cov%:</b> The fraction of items in this category
      <li><b>score:</b> The average score for items in this category
      <li><b>adj.score:</b> The adjusted (expected) score for new items, using the Laplace continuation formula
      <li><b>Signal:</b> The "interestingness" of the category, taken as the difference between the (adjusted) category score and overall score.
      <li><b><font color=green>Green Categories:</font></b> The score for these categories was greater than average
      <li><b><font color=red>Red Categories:</font></b> The score for these categories was lower than average	
    </ul>
    <p>
"""

TXT_LEGEND = """
CID: The ID of the category
Cov#: The total number of items in this category
Cov%: The fraction of items in this category
score: The average score for items in this category
adj.score: The adjusted (expected) score for new items, using the Laplace continuation formula
Signal: The \"interestingness\" of the category, taken as the difference between the (adjusted) category score and overall score. 
Green Categories: The score for these categories was greater than average
Red Categories: The score for these categories was lower than average 
"""

# ----------------------------------------------------------------------

### Returns an HTML/TXT table of the categories DataFrame
def categories_table_only(categories, cat_score_col:str='score', cat_adj_score_col:str='adj_score', cat_signal_col:str='signal', cat_title_col:str='title',
                          cat_description_col:str='description', format='html', tab='\t'):
  """Shows categories in a formatted table.

  Args:
    categories: A Pandas DataFrame with the provided columns PLUS built-in columns: n_covered, f_covered
    format: The desired format, one of 'latex', 'html', or 'txt'.
    tab: The delimiter for separating columns.

  Returns:
    A formatted string.
  """

  overall_average_score = categories.loc[0, cat_score_col]  
  overall_pc_score = round(overall_average_score * 100)
  n_tot = categories.loc[0, 'n_covered']
    
  categories = categories.sort_values(by='signal', ascending=False)  # Sort by signal

  ## title + first row
  output_str = ""
  if format == 'txt':
    output_str += f"CID{tab}cov#{tab}cov%{tab}score%{tab}adj.sc%{tab}Signal{tab}Done?{tab}title:desc\n"
    output_str += f"{''}{tab}{n_tot}{tab}{100}{tab}{overall_pc_score}%{tab}{overall_pc_score}%{tab}{0}{tab}{''}{tab}everything: The entire dataset\n"
  elif format == 'html':
    output_str += f'<table style="border:1px solid black;">\n'
    output_str += f'<tr><th>CID</th><th>cov#</th><th>cov%</th><th>score</th><th>adj.score</th><th>Signal</th><th>Category Title: Category Description</th></tr>\n'
    output_str += f'<tr><td></td><td><i>{n_tot}</i></td><td><i>100%</i></td><td><i>{overall_pc_score}%</i></td><td><i>{overall_pc_score}%</i></td><td><i>0</i></td><td><i>everything: The entire dataset</i></td></tr>\n'
  elif format == 'latex':
    output_str += f"\\begin{{center}}\n" \
                  f"  {{\\small\n" \
                  f"  \\setlength{{\\tabcolsep}}{{2pt}}    % narrower columns\n" \
                  f"  \\begin{{tabular}}{{|llllllp{{10cm}}|}} \\hline\n" \
                  f"  {{\\bf CID}} & {{\\bf cov\\#}} & {{\\bf cov\\%}} & {{\\bf score}} & {{\\bf adj.score}} & {{\\bf Signal}} & {{\\bf Category Title: Category Description}} \\\\ \\hline\n" \
                  f"  & {{\\it ~{n_tot}}} & {{\\it 1.00}} & {{\\it ~{overall_pc_score}\\%}} & {{\\it ~{overall_pc_score}\\%}} & {{\\it 0}} & {{\\it everything: The entire dataset}} \\\\ \\hline\n"

# for _, category in categories[categories['CID'] != 0].iterrows():
  for CID, category in categories.drop(0).iterrows():		# drop index 0 row
#   CID = category['CID']
    title = category[cat_title_col]
    description = category[cat_description_col]
    n_covered = category['n_covered']
    pc_covered = round(category['f_covered'] * 100)
    score = category[cat_score_col]
    adj_score = category[cat_adj_score_col] if category[cat_adj_score_col] != '?' else '?'
    pc_score = round(score * 100) if score != '?' else '?'
    adj_pc_score = round(adj_score * 100) if adj_score != '?' else '?'
    signal = round(category[cat_signal_col] * 100,1) if category[cat_signal_col] != '?' else '?'
    sign = "-" if adj_score != '?' and adj_score < overall_average_score else "+" if adj_score != '?' else " "
    color = 'green' if pc_score != '?' and pc_score > overall_pc_score else 'red' if pc_score != '?' and pc_score < overall_pc_score else 'black'
    done = ''
    is_from = ''           # or '(from CID)'

    if format == 'txt':
        output_str += f"{CID}{tab}{n_covered}{tab}{pc_covered}%{tab}{pc_score}%{tab}{adj_pc_score}%{tab}{sign}{signal}%{tab}{done}{tab}{title}: {description}{tab}{is_from}\n"
    elif format == 'html':
        output_str += f"<tr><td>{CID}</td><td>{n_covered}</td><td>{pc_covered}%</td><td>{pc_score}%</td><td>{adj_pc_score}%</td><td>{sign}{signal}%</td><td><b><font color={color}>{title}:</font></b> {description}{is_from}</td></tr>\n"
    elif format == 'latex':
        output_str += f"{CID} & {n_covered} & {pc_covered} & {pc_score}\\% & {adj_pc_score}\\% & {signal}\\% & {{\\bf \\{color}{{ {title}:}}}} {description} {is_from} \\\\~%"        

  if format == 'html':
      output_str += f"</table>"
  elif format == 'latex':
      output_str += f"\\hline \\end{{tabular}}\n}}\n\\end{{center}}"

  return output_str

### ======================================================================

"""
format_category_row(categories, dataset, 2, cat_title_col='title', cat_description_col='description', data_cat_col='categories', data_cols_of_interest=['question','answer'])



def format_category_row(categories:DataFrame, dataset:DataFrame, index:int, cat_title_col:str, cat_description_col:str, 
                        cat_score_col:str, data_cat_col:str, data_cols_of_interest:list, n_examples:int):
Purpose:
   Pretty-print the category at row index in a categories DataFrame, and optionally show n_examples illustrative examples.
Args:
    categories (DataFrame): A DataFrame with category information
    dataset (DataFrame): A DataFrame of objects (e.g., questions)
    index int): The category row to display
    cat_title_col (str): The categories column providing the title of each category
    cat_description_col (str): The categories column providing the description of each category
    cat_score_col (str): The categories column containing the overall category score
    data_cat_col (str): The column of dataset containing category membership information, in the form of a JSON array
    data_cols_of_interst (list): The names (strings) of the dataset columns to display, for the illustrative examples
    n_examples (int): The number of illustrative examples to show (default 1)
Returns: 
    The pretty-print of the category at index, as an HTML string 
Example:
    dataset = pd.DataFrame([{'question':'1+1?',  'answer': 2,'score':1.0, 'categories':[{'index':0,'score':1},{'index':1,'score':1.0},{'index':2,'score':0.0}]},
			    {'question':'20+20?','answer':40,'score':1.0, 'categories':[{'index':0,'score':1},{'index':1,'score':0.0},{'index':2,'score':1.0}]},
			    {'question':'2+2?',  'answer': 5,'score':0.0, 'categories':[{'index':0,'score':1},{'index':1,'score':1.0},{'index':2,'score':0.0}]}])
    categories = pd.DataFrame([{'title':'everything', 'description':'The entire dataset'},
                               {'title':'Single digit addition','description':'Math problems that involve only adding single digit numbers together'},
                               {'title':'Two digit addition','description':'Math problems that involve only adding two digit numbers together'}])
    output_text = format_category_row(categories, dataset, 2, cat_title_col='title', cat_description_col='description', 
                                      data_cat_col='categories', data_cols_of_interest=['question','answer'])
    print(output_text)
    <b>Two digit addition</b>: Math problems that involve only adding two digit numbers together (scored 100% [on 1 item], vs. 67% [on 3 items]). For example:
    <dd><dl>
    <dd><b>question:</b> 20+20?</dd>
    <dd><b>answer:</b> 40</dd>
   </dl></dd></ol>
"""
def format_category_row(categories, dataset, index, cat_title_col='title', cat_description_col='description', cat_score_col='score', data_cat_col='categories', data_cols_of_interest=[], n_examples=1, format='html'):

    row = categories.loc[index]
    title = row[cat_title_col]
    description = row[cat_description_col]
    cat_score = row[cat_score_col]
    category_pc_score = round(cat_score * 100)
    n_covered = row['n_covered']     # hard-wired column name
    n_total = len(dataset)
    overall_average_score = categories.loc[0, cat_score_col]  	# assume index 0 is the "Everything" category
    overall_pc_score = round(overall_average_score * 100)    
    plural = "s" if n_covered != 1 else ""

    if format == 'html':
        output_str = f"<b>{title}</b>: {description} (scored {category_pc_score}% [on {n_covered} item{plural}], vs. {overall_pc_score}% [on {n_total} items])."
    elif format == 'txt':
        output_str = f"**{title}**: {description} (scored {category_pc_score}% [on {n_covered} item{plural}], vs. {overall_pc_score}% [on {n_total} items])."
    else:
        raise Exception(f"Invalid format='{format}' in format_category_row")
        
    if n_examples > 0:
        if format == 'txt':
            output_str += " For example:\n\n"
        elif format == 'html':
            output_str += " For example:\n"

        # Find dataset examples of the category (location index)
        category_items = dataset[dataset[data_cat_col].apply(lambda x: any(category['index'] == index and category['score'] > 0.5 for category in x))]
        sorted_items = category_items.sort_values(by='score', ascending=False)

        for i, _ in sorted_items.head(n_examples).iterrows():
            output_str += format_dataset_row(sorted_items, i, data_cols_of_interest, format=format)

        if format == 'html':
            output_str += "</ol>\n"

    return output_str

### ======================================================================
###	format_dataset_row
### ======================================================================

"""
def format_dataset_row(dataset:DataFrame, index:integer, cols_of_interest:list):
Purpose:
    Create a HTML string representation of the row at index in dataset, showing the given columns of interest.
    This function is useful as a preprocessor for writing a report, to pretty-print an example for inclusion in the report.
Args:
    dataset (DataFrame): A DataFrame
    index (int): The index of the dataset row to display
    cols_of_interst (list): The names (strings) of the columns to display
Returns:
    string (str): An HTML pretty-print of that row
Example:
    dataset = pd.DataFrame([{"question":"1+1?","answer":2,"score":1.0},
                            {"question":"20+20?","answer":40,"score":1.0}])
    x = format_dataset_row(dataset, 1, cols_of_interest=['question','answer','score'])
    print(x)
    <dd><dl>
    <dd><b>question:</b> 20+20?</dd>
    <dd><b>answer:</b> 40</dd>
    <dd><b>score:</b> 1.0</dd>
    </dl></dd>
"""

def format_dataset_row(dataset, index, cols_of_interest:list, format='html'):
    row = dataset.loc[index]
    string = "<dd><dl>\n" if format == 'html' else ""
    for col in cols_of_interest:
        if format == 'html':
            string += f"<dd><b>{col}:</b> {row[col]}</dd>\n"
        else:
            string += f" * **{col}**: {row[col]}\n"
    string += "</dl></dd>" if format == 'html' else ""
    return string
        
