"""
Reflect
Do a reflection
-------
{...}
-------
Thought:I've done step 3. Move to step 4 (write report)
Now generate an action
----------
{action:"write_report('olmo')"}
----------
Action: ...
Executing...
In [123]: write_report('olmo')
Generating report using GPT:
> Create a title for the report.
afadadsf
> Write a paragraph
...
"""

import os
import pprint
import time
import datetime
import pandas as pd
import json
from string import Template		# for write_report()

from . import my_globals
from .format_dataset import dataset_table_only, dataset_table_legend
from .format_categories import categories_table_only, categories_table_legend
from panda.utils import replace_special_chars_with_ascii, call_llm, call_llm_json, get_token_counts, remove_html_markup, extract_html_from_string
from . import config as agent_config
# Below purely to get researchworld.tools.created_datasets and researchworld.tools.created_categories vars (rather than a COPY of those vars at import time, voa from ... import ..)
#import panda.researchworld.tools as tools
import panda.researchworld.tools as tools
import panda.researchworld.ideate_categories as ideate_categories

### --------------------

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# NEW: Assume run_panda will create and enter a working directory for the research artifacts
# REPORT_DIR = os.path.abspath(os.path.join(MODULE_DIR, "../../output/"))   # abs to factor out ".." in the path string
REPORT_DIR = "."    # assume the local dir is the one

REPORT_HTML_TEMPLATE_FILE = os.path.join(MODULE_DIR, "report_template.html")
REPORT_TXT_TEMPLATE_FILE = os.path.join(MODULE_DIR, "report_template.txt")	# no longer used

with open(REPORT_HTML_TEMPLATE_FILE, 'r') as f:
    REPORT_HTML_TEMPLATE = f.read()
with open(REPORT_TXT_TEMPLATE_FILE, 'r') as f:
    REPORT_TXT_TEMPLATE = f.read()    

### --------------------

REPORT_FORMAT = "plain text"  # or "html"

GATHER_RESULTS_PROMPT = """Review the conversation so far and identify any experimental result summaries that should be included as tables in a final report. 
Only gather summary statistics, not individual item scores here. 
Write out those summary statistics as a JSON structure. I'll refer to these tables as the "RESULTS_JSON_STRUCTURE". """    # JSON structure of GPT's choice!

GATHER_EXAMPLES_PROMPT = """Review the conversation so far and identify any useful examples that should be included in a final report, that are illustrative of the findings.
Write out those examples as a JSON structure. I'll refer to this data as the "EXAMPLES_JSON_STRUCTURE". """    # JSON structure of GPT's choice!

REPORT_INTRO = """I'm now going to ask you to write a report about the research conducted, section by section.
Before starting, think about what the main conclusions are that you want the report to make, and plan the report contents accordingly so the report is coherent.
The experiments should describe pertinent results supporting the conclusions.
The analysis should describe analytical reflections about the results, for example describing interesting categories of problem/task that provide interesting insights.
As a preview, the report will contain the following sections:
 - title
 - abstract
 - introduction
 - approach
 - results
 - analysis
 - conclusion
I'll now ask you for each section in turn. Just provide the information for the section that I ask for, and nothing else. Do not provide other sections until prompted.
Let's begin!"""

CAUTION = " BE CONSERVATIVE: Don't overclaim more than the experiments justify. If results are unclear or inconclusive, say so. It is very important you are honest and cautious - lives may hang in the balance."

REPORT_PARTS = \
 {"title": "First, create a title for the report.", \
  "abstract": "Write an abstract for the report. State the goal, then the approach, then the findings, then a statement about the significance of the work." + CAUTION, \
  "introduction": "Write an introduction. Describe the motivation for the work, then give an overview of what was done, and finally the main findings." + CAUTION, \
  "approach": "Describe the approach used in detail.", \
  "results": """Describe the experimental results that were obtained.
Use the RESULTS_JSON_STRUCTURE that you generated earlier to create one or more tables of experimental results to include in this Section.
""",
#  "results_html": """Describe the experimental results that were obtained.
#Use the RESULTS_JSON_STRUCTURE that you generated earlier to create one or more tables of experimental results to include in this Section.
#""",  
  "analysis": """
Write an analysis of the results. Use the EXAMPLES_JSON_STRUCTURE that you generated earlier to provide illustrative examples for this section, to make your points clear. When you provide examples, make sure you provide all the details so the reader understands.""",
#  "analysis_html": """
#Write an analysis of the results. Use the EXAMPLES_JSON_STRUCTURE that you generated earlier to provide illustrative examples for this section, to make your points clear. When you provide examples, make sure you p#rovide all the details so the reader understands.""",  
#For example, do not write things like:
#    "For instance, in one question, OLMo provided a correct final answer but used an 
#     incorrect method involving swapping tens and ones digits in its explanation."
#Instead, show the example question and answer so the reader can see what you mean, e.g., write:
#    "For instance, in one question:
#     <ul>
#      <li> <b>Question:</b> What is 47 + 26?
#      <li> <b>OLMO's answer:</b> The sum of 47 and 26 is 73. You can also solve this problem using mental math:<br>First, add the tens digits: 7 + 2 = 9.<br>Then, add the ones digits: 4 + 6 = 10.<br>Since 10 is greater than or equal to the next ten, you can carry the 1 to the next addition: 9 + 1 = 10.<br>So, 47 + 26 = 73.   
#     </ul>
#    OLMo provided a correct final answer but used an incorrect method involving swapping tens and ones digits in its explanation:"
#""",
  "conclusion": "Summarize conclusions of the research, in particular the main findings." + CAUTION}

DATASETS_PROMPT = """Did you create any datasets (stored in DataFrames) in this research? If so, provide a list of the variables used to store them.
Return your answer as a compact JSON object, formatted as a single line with no unnecessary spaces or newlines, in the following structure: {'answer': [{'dataset':VARIABLE},{'dataset':VARIABLE2},...]}.
If you did not create any datasets, return just {'answer':[]}"""

CATEGORIES_PROMPT = """Did you create any DataFrames for categories in this research? If so, provide a list of the variables used to store them.
Return your answer as a compact JSON object, formatted as a single line with no unnecessary spaces or newlines, in the following structure: {'answer': [{'categories':VARIABLE},{'categories':VARIABLE2},...]}.
If you did not create any DataFrames for categories, return just {'answer':[]}"""

### ======================================================================
### 			WRITE A REPORT
### Pass the entire conversation history to GPT to write up the work
### ======================================================================

agent_config.doc['write_report'] = """    
def write_report():
Purpose:
    Writes a report to a file, and also prints it out as a text file in stdout.
    The report summarizes the research performed in the current dialog history.
    IMPORTANT: Make sure that all the information (examples etc.) required for the report is visible in the conversational history, as write_report() turns that history into a report.
    If it is not, first print out the required information (examples, tables, etc.)
Args:
    None
Returns:
    The path stem to the reports. Add the suffixes ".txt" or ".html" to the stem for the path to the plain text / HTML report file, respectively.
	
Example:
    write_report()
->  Reports written to:
    - c:/Users/peter/Desktop/panda/output/experiment-20250705-213812/experiment.html
    - c:/Users/peter/Desktop/panda/output/experiment-20250705-213812/experiment.txt
    # and returns the stem "c:/Users/peter/Desktop/panda/output/experiment-20250705-213812/experiment"
"""
def write_report(filename="report", report_dir=REPORT_DIR, timestamp=True, input_dialog=None, model=agent_config.REPORT_WRITER_LLM):

    if not input_dialog:
        input_dialog = my_globals.dialog_so_far		# the last item in dialog_so_far will be a GPT response
    report_dialog = input_dialog.copy()        
            
    html_report_template = Template(REPORT_HTML_TEMPLATE)
    txt_report_template = Template(REPORT_TXT_TEMPLATE)    
    report_parameters = {}				# empty dict
    print("\nGenerating report using GPT:\n")

    # get some useful JSON
    make_report_prequeries(report_dialog)
    
    for section, prompt in REPORT_PARTS.items():
        prompt = (REPORT_INTRO + prompt) if section == "intro" else prompt
        prompt += f"\nReturn exactly and only the {section}, so it can be directly included in the report. Do not return any additional justification or explanation.\n"
        if REPORT_FORMAT == "html" or section.endswith("_html"):
            prompt += "If you do any formatting, use HTML markup rather than Markdown (md) markup. e.g., for a numbered list, use <ol><li>...<li>...</ol>."
        else:
            prompt += "Return the response in plain text format (including tabulating tables with spaces). Do not use HTML or Markdown."
        report_dialog += [prompt]
        print("------------ Query -----------------------")
        print(prompt)
        print("---------- GPT Reponse  ------------------")
        response0 = call_llm(report_dialog, model=model)
        response = replace_special_chars_with_ascii(response0)		# get rid of non-ASCII characters that mess up the display
        report_dialog += [response]
        print(response[:70], "...", sep="")			# truncate the response when printing to the terminal
        report_parameters[section] = response

    dataset_named_dataframes, categories_named_dataframes = get_dataframes_for_appendix(report_dialog)
    nice_dataframes_txt, nice_dataframes_html = format_nice_dataframes(dataset_named_dataframes, categories_named_dataframes)
    all_dataframes = get_dataframes(my_globals.code_so_far)
    all_dataframes_txt = ""
    all_dataframes_html = ""    
    if all_dataframes:
        all_dataframes_txt = "Appendix: Summary of All DataFrames\n-----------------------------------\n\n"
        all_dataframes_html = "<h3>Appendix: Summary of All DataFrames</h3>\n\n"
        for dataframe_name, dataframe in all_dataframes:
            all_dataframes_txt += dataframe_name + "\n" + "-" * len(dataframe_name) + "\n" + summarize_df_with_ellipsis(dataframe) + "\n"
            all_dataframes_html += "<pre>\n" + dataframe_name + "\n" + "-" * len(dataframe_name) + "\n" + summarize_df_with_ellipsis(dataframe) + "\n</pre>\n"
        			     
    report_parameters['notes'] = footnotes()
    report_parameters['date'] = datetime.datetime.now().strftime("%m-%d-%Y %H:%M:%S")
    report_parameters['underline'] = "=" * len(report_parameters['title'])		# for .txt output
    report_parameters['html_dataframes'] = nice_dataframes_html
    report_parameters['txt_dataframes'] = nice_dataframes_txt
    report_parameters['html_all_dataframes'] = all_dataframes_html
    report_parameters['txt_all_dataframes'] = all_dataframes_txt    

    txt_report = txt_report_template.substitute(report_parameters)    
    html_report = html_report_template.substitute(report_parameters)    

#    if REPORT_FORMAT == "html":
#        html_report = html_report_template.substitute(report_parameters)
#        txt_report = convert_html2txt(html_report)
#    else:
#        txt_report = txt_report_template.substitute(report_parameters)
#        html_report = convert_txt2html(txt_report)        

    return save_report(html_report=html_report, txt_report=txt_report, filename=filename, report_dir=report_dir, timestamp=timestamp, input_dialog=input_dialog)

# ----------                                      

def summarize_df_with_ellipsis(df):
    if len(df) <= 10:
        return df.to_string()
    else:
        head_str = df.head(5).to_string()
        tail_str = df.tail(5).to_string(index=False)  # Avoid duplicate index column
        ellipsis_line = "..."
        return f"{head_str}\n{ellipsis_line}\n{tail_str}"

# ----------

def make_report_prequeries(report_dialog):    
    # First, reflect on the experiment and gather the experimental results together
    print("------------ Query -----------------------")
    print(GATHER_RESULTS_PROMPT)
    report_dialog.append(GATHER_RESULTS_PROMPT)
    print(f"---------- {agent_config.PANDA_LLM} Reponse  ------------------")    
    response_str = call_llm(report_dialog, model=agent_config.PANDA_LLM)
    report_dialog.append(response_str)
#   print(response_str[:70], "...", sep="")			# truncate the response when printing to the terminal
    print(response_str)

    # Now, reflect on the experiment and gather illustrative examples
    print("------------ Query -----------------------")
    print(GATHER_EXAMPLES_PROMPT)
    report_dialog.append(GATHER_EXAMPLES_PROMPT)
    print(f"---------- {agent_config.PANDA_LLM} Reponse  ------------------")    
    response_str = call_llm(report_dialog, model=agent_config.PANDA_LLM)
    report_dialog.append(response_str)
#   print(response_str[:70], "...", sep="")			# truncate the response when printing to the terminal
    print(response_str)    

# ----------    

def save_report(html_report, txt_report, filename="report", report_dir=REPORT_DIR, timestamp=True, input_dialog=None):
#    date_for_filename = datetime.datetime.now().strftime("%m-%d-%Y_%H.%M")        
#    tweaked_filename = filename + "_" + date_for_filename if timestamp else filename
#    report_pathstem = os.path.join(report_dir, tweaked_filename)

    report_pathstem = my_globals.last_report_pathstem

    html_report_file = report_pathstem + ".html"
    with open(html_report_file, "w", encoding='utf-8', errors='replace') as file:
        file.write(html_report)

    txt_report_file = report_pathstem + ".txt"
    with open(txt_report_file, "w", encoding='utf-8', errors='replace') as file:
        file.write(txt_report)

#    if input_dialog:        
#        json_report_file = report_pathstem + ".json"		# store the raw input data, minus DataFrames
#        with open(json_report_file, "w", encoding='utf-8', errors='replace') as f:
#            json.dump(input_dialog, f, indent=4)    

    my_globals.last_report_pathstem = report_pathstem		# Rather hacky way of making a note if a file was generated
    print(txt_report)
    print("----------------------------------------------------------------------")
    print("Reports written to:")
    print(" -", html_report_file)
    print(" -", txt_report_file)
#    print(" -", json_report_file)        
    return report_pathstem

# ------------------------------

def convert_html2txt(html_report):
    print(f"Converting report from HTML to TXT using {agent_config.REPORT_TRANSLATOR_LLM}...")
    txt_report = call_llm(f"""Convert the following HTML file into plain text. Return just the text, without any commentary before or after.
```html
{html_report}
```
""", model=agent_config.REPORT_TRANSLATOR_LLM)
    return extract_txt_from_string(txt_report)

def convert_txt2html (txt_report):
    print(f"Converting report from TXT to HTML using {agent_config.REPORT_TRANSLATOR_LLM}...")
    html_report = call_llm(f"""Format the following text file into HTML. Return just the HTML, without any commentary before or after.
```text
{txt_report}
```
""", model=agent_config.REPORT_TRANSLATOR_LLM)
    return extract_html_from_string(html_report)

# ------------------------------

def footnotes():
    runtime_seconds = time.time() - my_globals.start_time if my_globals.start_time else None
    runtime = round(runtime_seconds / 60) if runtime_seconds else "?"
    token_counts = get_token_counts()
    notes = get_token_summary(token_counts) + "\n"
    notes += f"Runtime: {runtime} minutes.\n"
    return notes

def get_token_summary(token_counts):
    parts = [
        f'{entry["model"]}: {entry["total_tokens"]} tokens'
        for entry in token_counts
    ]
    summary = "; ".join(parts)
    return summary

# ======================================================================
#	GET DATAFRAMES OF INTEREST
# ======================================================================

## MUCH simpler - just use global variables to track created datasets and categories!
## RETURNS: two values, each a list of (pair) tuples ("dataset|categories",DataFrame)    (DataFrame is the actual dataframe, not a variable name)
def get_dataframes_for_appendix(report_dialog=None):
    dataset_named_dataframes = []
    for created_dataset in tools.created_datasets:
        dataset_named_dataframes += [("dataset",created_dataset)]

    categories_named_dataframes = []
    for created_category in ideate_categories.created_categories:
        categories_named_dataframes += [("categories",created_category)]    

    return dataset_named_dataframes, categories_named_dataframes    

# ----------

# input: two lists of ("dataset|categories",DataFrame) 2-tuples
def format_nice_dataframes(dataset_named_dataframes, categories_named_dataframes):    
    #   (c.1) prints them into the report (phew!)
    if dataset_named_dataframes == []:
        html_dataset_str = ""        
        txt_dataset_str = ""
    else:
        html_dataset_str = "<h3>Appendix: Summary of Datasets</h3>\n\n" + dataset_table_legend()
        txt_dataset_str = "Appendix: Summary of Datasets\n" + "-----------------------------\n\n" + dataset_table_legend(format='txt')
        for name, dataframe in dataset_named_dataframes:
            try:
                html_dataset_str += "\n<p>\n<b>" + name + ":</b>\n<p>\n" + dataset_table_only(dataframe)	# no legend
                txt_dataset_str += "\n\n" + name + ":\n\n" + dataset_table_only(dataframe, format='txt')	# no legend                
            except:
                html_dataset_str += f"(Generation of table {dataframe} failed)"
                txt_dataset_str += f"(Generation of table {dataframe} failed)"                
#   report_parameters['dataset'] = html_dataset_str - later
    
    #   (c.2) prints them into the report (phew!)
    if categories_named_dataframes == []:
        html_categories_str = ""        
        txt_categories_str = ""
    else:
        html_categories_str = "<h3>Appendix: Summary of Categories</h3>\n\n" + categories_table_legend()
        txt_categories_str = "Appendix: Summary of Categories\n" + "-------------------------------\n\n" + categories_table_legend(format='txt')
        for name, dataframe in categories_named_dataframes:
            try:
                html_categories_str += "\n<p>\n<b>" + name + ":</b>\n<p>\n" + categories_table_only(dataframe)	# no legend
                txt_categories_str += "\n\n" + name + ":\n\n" + categories_table_only(dataframe, format='txt')	# no legend                
            except:
                html_categories_str += f"(Generation of table {dataframe} failed)"
                txt_categories_str += f"(Generation of table {dataframe} failed)"                
#   report_parameters['categories'] = html_categories_str - later

    nice_dataframes_txt = txt_dataset_str + txt_categories_str
    nice_dataframes_html = html_dataset_str + html_categories_str
    return nice_dataframes_txt, nice_dataframes_html
    
### ======================================================================
###		print out the dialog so far (both SHORT and LONG versions)
### ======================================================================

### save_dialog(["You are a smart assistant.","What is 1+1?","2","What is 2+3?"])
### save_dialog(output_filestem="report-trace")
### Note: "-trace.txt", "-trace-long.txt", and ".py" will be concatenated to output_filestem
def save_dialog(dialog=None, show_system_prompt=True, output_dir=REPORT_DIR, output_filestem=None, observations=None):
    if dialog is None:
        if my_globals.dialog_so_far:
            dialog = my_globals.dialog_so_far  # Dynamically assign the current value
        else:
            raise ValueError("No dialog to save! my_globals.dialog_so_far and the argument save_dialog(dialog=<>,..) are both None!")

    if not output_filestem and my_globals.last_report_pathstem:	# INCLUDES output directory
        output_pathstem = my_globals.last_report_pathstem
    else:
        if not output_filestem:
            output_filestem = datetime.datetime.now().strftime("%m-%d-%Y_%H.%M")
        os.makedirs(output_dir, exist_ok=True)            	# create directory if needed
        output_pathstem = os.path.join(output_dir, output_filestem)

    output_trace_path = output_pathstem + "-trace.txt"
    output_longtrace_path = output_pathstem + "-trace-long.txt"
    output_code_path = output_pathstem + ".py"
    output_dataset_stem = output_pathstem + "-df-"

    # 1. Print out the short trace (what the user sees)
    with open(output_trace_path, 'w', encoding='utf-8', errors='replace') as file:
        file.write(my_globals.print_so_far)

    # 2. Print out the long trace (the exact dialog with GPT)
    with open(output_longtrace_path, 'w', encoding='utf-8', errors='replace') as file:

        def write_output(text):
            file.write(text + "\n")

        write_output(agent_config.SYSTEM_PROMPT_HEADER)
        write_output("")

        if show_system_prompt:
            write_output(dialog[0])			# SYSTEM_PROMPT + background_knowledge
        else:						# just show the task part of the prompt
            write_output("...<system prompt + background_knowledge>...")
            cutpoint = dialog[0].find("-- end of system prompt --")
            if cutpoint!= -1: 				# Check if substring was found
                write_output("\n\n" + dialog[0][cutpoint:])

        write_output("")
        # Loop over every 2 items starting at index 1
        for i in range(1, len(dialog), 2):
            write_output(agent_config.PANDA_HEADER)
            write_output(dialog[i])

            if i + 1 < len(dialog):  # Check if the next item exists
                write_output(agent_config.GPT_HEADER.format(PANDA_LLM=agent_config.PANDA_LLM))
                write_output(dialog[i + 1])

        if observations:   # extra last output that didn't make it into dialog
            write_output(agent_config.PANDA_HEADER)
            write_output(observations)

    # 3. Print out the code
    code = my_globals.code_so_far
    with open(output_code_path, "w", encoding='utf-8', errors='replace') as file:
        file.write(code)

    # 4. Save artifacts to files....
#    dataset_n = 0
#    named_dataframes = get_dataframes(my_globals.code_so_far)
#    for dataframe_name, dataframe in named_dataframes:
#        dataset_filename = output_dataset_stem + dataframe_name + ".json"
#        dataframe.to_json(dataset_filename, orient="records", lines=True)		# This WRITES the full dataset to the file

    named_vars = get_vars(my_globals.code_so_far)
#   print("DEBUG: named_vars =", named_vars)
    if named_vars:
        vars_filename = output_pathstem + "-artifacts.py"        
        with open(vars_filename, "w", encoding='utf-8', errors='replace') as file:
            for var_name, var in named_vars:
                print("Doing", var_name)
                if isinstance(var, pd.DataFrame):
                    file.write("\nimport pandas as pd\n")
                    dict_rows = var.to_dict(orient='records')
                    pretty_rows = pprint.pformat(dict_rows, indent=2)	# add newline for each row
                    file.write(f"\n{var_name}_rows = {pretty_rows}\n")
                    file.write(f"{var_name} = pd.DataFrame({var_name}_rows)\n\n# ----------\n\n")
# version 1         file.write(f"\n{var_name} = pd.DataFrame({var.to_dict(orient='records')})\n\n# ----------\n\n") # one long line (unreadable)
                else:
                    file.write(f"\n{var_name} = {repr(var)}\n\n# ----------\n\n")

    print(f"Dialog, code, and dataframes saved to files {output_pathstem}*")

### ========================================

# returns a list of the form [('my_dataset',my_dataset),...]
def get_dataframes(code):
    prompt = """Read the following code, and then return a list of all the dataframes created in it (if any).
========================================
      START OF CODE	
========================================
""" + code + """
========================================
      END OF CODE	
========================================
Now return a list of all the dataframes created in it (if any).
Return your answer as a JSON structure of the form:
    {"dataframes":[dataframe1,...,dataframeN]}
listing the variable name of each data frame."""
    dataframes_json, dataframes_str = call_llm_json(prompt, model=agent_config.PANDA_LLM)
    dataframe_names = dataframes_json['dataframes']

    nspace = my_globals.state['state'].namespace    # This is where I squirrel away the exec() namespace
    named_dataframes = [
        (dataframe_name,nspace[dataframe_name])			    # Access the variable from nspace using its name
        for dataframe_name in dataframe_names
        if dataframe_name in nspace and isinstance(nspace[dataframe_name], pd.DataFrame)	# safety check to avoid hallucinations, avoid DataFrames
    ]
    return named_dataframes

#----------

# returns a list of the form [('profiles',profiles),...]
def get_vars(code):
    prompt = """Read the following code, and then return a list of all the variables (if any) that contain key data, e.g., a dataset, that a researcher might want to see to understand what the code actually did, and to potentially reuse in future experiments.
========================================
      START OF CODE	
========================================
""" + code + """
========================================
      END OF CODE	
========================================
Now return a list of all the key variables created in it (if any).
Return your answer as a JSON structure of the form:
    {"variables":[var1,...,varN]}
"""
    vars_json, vars_str = call_llm_json(prompt, model=agent_config.PANDA_LLM)
    var_names = vars_json['variables']

    nspace = my_globals.state['state'].namespace    # This is where I squirrel away the exec() namespace
    named_vars = [
        (var_name,nspace[var_name])			    # Access the variable from nspace using its name
        for var_name in var_names
#       if var_name in nspace and not isinstance(nspace[var_name],pd.DataFrame)	# SKIP DataFrames (can't print them in a readable way so easily)
        if var_name in nspace
    ]
#   print("DEBUG: vars found in code:", var_names)
    return named_vars

    
    
