"""
dataset:
number of examples:
score: min: 0.00; max: 1.00; mean: 0.43; variance: 0.35
"""

import pandas as pd

# Don't need a legend for datasets
HTML_LEGEND = ""
TXT_LEGEND = ""

def dataset_table_legend(format='html'):
    if format == 'html':
        return HTML_LEGEND
    elif format == 'txt':
        return TXT_LEGEND
    else:
        raise Exception(f"Unrecognized format='{format}' in categories_table_with_legend!")

# Returns a string summarizing the dataframe    
def dataset_table_only(dataset, format='html'):
    output_str = "Number of examples: " + str(len(dataset)) + "\n"
    numeric_cols = get_numeric_columns(dataset)
    output_str += "<ul>\n" if format == 'html' else ""
    for numeric_col in numeric_cols:
         min_val = dataset[numeric_col].min()
         max_val = dataset[numeric_col].max()
         mean_val = dataset[numeric_col].mean()
         variance_val = dataset[numeric_col].var()
         values = dataset[numeric_col].tolist()

         output_str += "<li> " if format== 'html' else " - "
         output_str += f"<b>{numeric_col}:</b> " if format == 'html' else f"{numeric_col}: "
         output_str += f"min: {min_val:.2f}; max: {max_val:.2f}; mean: {mean_val:.2f}; variance: {variance_val:.2f};\n"
         output_str += f"<br><b>{numeric_col} values:</b> [ " if format == 'html' else f"   {numeric_col} values: [ "
         output_str += ", ".join(f"{value:.2f}" for value in values)
         output_str += " ]\n"
    output_str += "</ul>\n" if format == 'html' else ""
    output_str += "First five rows:\n"
    output_str += "<pre>" if format == 'html' else ""
    output_str += dataset.head(5).to_string(index=False)
    output_str += "</pre>" if format == 'html' else ""    
    return output_str

# ----------

def get_numeric_columns(df):
  """
  Identifies and returns a list of column names that contain numeric data.
  """
  numeric_cols = df.select_dtypes(include='number').columns.tolist()
  return numeric_cols 	# e.g., 'score'
