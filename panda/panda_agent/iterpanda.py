"""

Usage:
panda.run_iterpanda(logbook_file="logbook.md")
where logbook.md might start:
"# Research Mission
 How much does an in-context fact influence model behavior?"

Given a top-level Mission (and optional task):
0. (If no task is provided, ideate a task [possibly using step 2 functions])
1. Do an experiment
2. Review the results, and ideate possible follow-on experiments
3. Select the follow-on experiment that will most help towards the Mission

Example Missions: 
 - I want to build the best tunable hypothesis generator 
 - I want to distill a rulebase articulating a LM's apparent ethical decision-making rules
 - I want to characterize how good my LM is at math

How the Iternora dialog_so_far is built up over time (saved as a single string iterpanda_trace.txt)
  itenora_dialog = [mission,"ok",task1 + execution_trace_inc_report + "possible next tasks?",<list>,"pick one",<choice>,"I did it, and here's the results" + execution_trace_inc_report]
NOTE: with the logfile, we use single shot (no message list) prompt as follows:
  prompt = [intro + iterpanda_dialog + logfile + "reflection?",reflection,"possible next tasks?",<list>,"pick one",<choice>]
   -> run_panda(task=<choice>, background_knowledge="Here's what we've done so far"+iterpanda_dialog+"end")
   <- execution_trace [+ URLs of artifacts]

----------

How the iteration works:

First a SINGLE prompt (no history):
  prompt = [intro + iterpanda_dialog(initially empty) + logfile] now ask and extend with ["possible next tasks?",<list>,"pick one",<choice>]

  itenora_dialog = [initial_logfile+"possible next tasks?",<list>,"pick one",<choice>]
   -> run_panda(task=<choice>, background_knowledge="Here's what we've done so far"+iterpanda_dialog+"end")    
   <- execution_trace [+ URLs of artifacts]
[1]itenora_dialog = [initial_logfile+"possible next tasks?",<list>,"pick one",<choice>,"I did it and here's the results" + execution_trace_inc_report + "generate a summary for the LOGBOOK."]
   <- addition for logbook
Now a SINGLE prompt (no history):
  prompt = [intro + iterpanda_dialog(minus "generate summary") + updated_logfile + "reflection?",reflection,"possible next tasks?",<list>,"pick one",<choice>]
   -> run_panda(task=<choice>, background_knowledge="Here's what we've done so far"+iterpanda_dialog+"end")    
   <- execution_trace [+ URLs of artifacts]
  NOW: extend iterpanda_dialog with memorized [..."possible next tasks?",<list>,"pick one",<choice>,"I did it, and here's the results" + execution_trace_inc_report]
  Goto [1]

NEW:
experiments_trace = ["EXPERIMENT 1" + experiment_trace + "EXPERIMENT 2" + experiment_trace + ...]

1. Single message prompt to decide what to do next (in two parts)
  [main_intro+experiments_trace+logbook+"what next?"] -> <list> -> "pick one" -> <choice>
2. parameters for run_panda: task=<choice>, background_knowledge=experiments_trace+logbook -> execution_trace
3. Prompt for experimental summary:
  [main_intro+experiments_trace+logbook+"I did this next experiment, please add to the logook" + execution_trace + "What shall I add to the logbook?"]
  a. updated logbook
  b. add ["EXPERIMENT 3" + experiment_trace] to experiments_trace
  c. Goto 1

etc.

"""
import os
import re
import datetime, string
from enum import Enum
from pydantic import BaseModel, Field

from . import config as agent_config
from . import my_globals         # for my_globals.print_so_far from panda
from panda.utils import call_llm, call_llm_json, read_file_contents, clear_directory, copy_file, file_exists

# ----------

# local var, for now
iterpanda_dialog = []
MAX_ITERATIONS = 1
MAX_RETRIES = 3
REPORT_EXT = ".txt"
ALLOW_SHORTCUTS = False

LOGFILE = "logbook.md"

MAIN_INTRO = """
INTRODUCTION
------------
I'm wanting to use an Autonomous Scientific Discovery (ASD) system to help me with the below research mission. I'm part way through this research, and below you'll see:
 (1) A DETAILED TRACE of the experiments we've done so far
 (2) A top-level LOGBOOK which summarizes the experiments, main findings, and directions
Read through these, and then at the end provide direction on what to do next, responding to the prompt that you will see there.
"""

PART_ONE_HEADER = """
======================================================================
======================================================================
	PART ONE: DETAILED TRACE OF WORK SO FAR		
======================================================================
======================================================================
"""

PART_TWO_HEADER = """
======================================================================
======================================================================
	PART TWO: LOGBOOK
======================================================================
======================================================================
"""
DASHES = """
----------------------------------------------------------------------
"""


""" 
======================================================================
	MAIN ENTRY POINT
======================================================================
panda.run_iterpanda(logbook_file="logbook.md")
"""
def run_iterpanda(logbook_file=None):

    global iterpanda_dialog
    
    # ----------------------------------------
    # STEP 1: Initialization and load logbook
    # ----------------------------------------
    os.chdir(agent_config.ROOT_DIR)			# make sure you're back at the top
    if not file_exists(logbook_file):
        message = f"ERROR! No such logbook file '{logbook_file}'!"
        print(message)
        raise ValueError(message)
    with open(logbook_file, "r", encoding="utf-8", errors='ignore') as f:
        logbook = f.read()    

    # ----------------------------------------
    # STEP 2: Decide what experiment to do next and do it
    # ----------------------------------------
    experiments_trace, last_experiment_number = collect_experiments_trace(logbook)
    iterpanda_dialog = [MAIN_INTRO + PART_ONE_HEADER + experiments_trace + PART_TWO_HEADER + logbook]
    task = get_next_task(logbook)
    
    background_knowledge = """
==================== START OF WHAT WE'VE DONE TOGETHER SO FAR ====================
Here's what we've done together so far:
""" + experiments_trace + """
==================== END OF WHAT WE'VE DONE TOGETHER SO FAR ====================
"""
    report_result, report_pathstem, report_summary = run_iterpanda_experiment(task, background_knowledge=background_knowledge)
    print("DEBUG: report_result =", report_result)
    print("DEBUG: report_pathstem =", report_pathstem)
    print("DEBUG: report_summary =", report_summary)

    experiment_trace = my_globals.print_so_far		# *excudes* SYSTEM_PROMPT + background_knowledge, so we don't double up. This content is stored in "...-trace.txt" in the experiment's directory

    # ----------------------------------------
    # STEP 3: Generate a summary of the experiment for the logbook
    # ----------------------------------------    

    summary_for_logbook_prompt = """
========================================
Now: Please provide a short summary of the experiment to add to the LOGBOOK, to help future researchers learn from this new experiment. Use Markdown (MD) format.
Give the experiment a title, and describe the goal, approach, and findings. The findings should describe the important take-aways from the experiment, to help choose future experiments that will contribute further to the overall mission.

For example:

#### **Experiment: Foundational System Implementation and Initial Evaluation**
- **Goal:** Implement an LLM-based hypothesis generator, a simulated research agent with profiles of varying capability, and a feedback loop to tune the hypothesis generator using failure explanations.
- **Approach:** For several simulated agent profiles of differing capability (e.g., having access to only local code/data, or web APIs, or just paper/pencil), ran iterative experiments where the hypothesis generator produced hypotheses per provided advice; agent feedback (whether a hypothesis was testable and, if not, why) was used to update the advice.
- **Findings:** The generator adapted easily to some agent profiles, yielding high rates of testable hypotheses; with more constrained agents, adaptation was much harder—success rates were very low and advice updates less effective. This highlighted a key challenge: adaptation is highly sensitive to the underlying agent capabilities and feedback strategy.

(end of example)
Do not provide any additional information, only provide EXACTLY what should be added at the end of the LOGBOOK, in Markdown (MD) format. Go ahead!"""

    full_summary_for_logbook_prompt = "Thanks! Ok, I've taken your advice and performed this new experiment. The results are as follows:\n" + experiment_trace + summary_for_logbook_prompt

    my_print(summary_for_logbook_prompt, 'IterPanda')
    iterpanda_dialog.append(full_summary_for_logbook_prompt)
    response_str  = call_llm(iterpanda_dialog, model=agent_config.ITERPANDA_LLM)
    my_print(response_str, agent_config.ITERPANDA_LLM)
    iterpanda_dialog.append(response_str)    

# HTML version
#   report_href = f'<a href="{report_pathstem}.txt">report</a>, ' if file_exists(f"{report_pathstem}.txt") else ""    
#   code_href = f'<a href="{report_pathstem}.py">code</a>, ' if file_exists(f"{report_pathstem}.py") else ""
#   artifacts_href = f'<a href="{report_pathstem}-artifacts.py">artifacts</a>, ' if file_exists(f"{report_pathstem}-artifacts.py") else ""
#   trace_href = f'<a href="{report_pathstem}-trace.txt">trace</a>'
#   file_hrefs = "(" + report_href + code_href + artifacts_href + trace_href + ")"

# MD version
    report_href = f"[report]({report_pathstem}.html), " if file_exists(f"{report_pathstem}.html") else ""	# switched to HTML
    code_href = f"[code]({report_pathstem}.py), " if file_exists(f"{report_pathstem}.py") else ""
    artifacts_href = f"[artifacts]({report_pathstem}-artifacts.py), " if file_exists(f"{report_pathstem}-artifacts.py") else ""
    trace_href = f"[trace]({report_pathstem}-trace.txt)"
    file_hrefs = "(" + report_href + code_href + artifacts_href + trace_href + ")"

    logbook_entry = DASHES + f"EXPERIMENT {str(last_experiment_number+1)} {file_hrefs}\n------------\n" + response_str
    add_to_end_of_file(logbook_entry, logbook_file)		# Extend the logbook    

    # ----------------------------------------
    # STEP 4: Generate some recommendations for next steps
    # ----------------------------------------

    # reread the updated logbook and experiments
    with open(logbook_file, "r", encoding="utf-8", errors='ignore') as f:
        logbook = f.read()
    experiments_trace, last_experiment_number = collect_experiments_trace(logbook)         

    task_recommendations = get_task_recommendations()
    add_to_end_of_file(task_recommendations, logbook_file)		# Extend the logbook        

#------------------------------

def add_to_end_of_file(string, file):
    with open(file, "a", encoding="utf-8", errors='ignore') as file:
        file.write(string)

# ======================================================================
#	RUN THE ACTUAL EXPERIMENT
# ======================================================================        

# NOTE: reset_namespace, reset_dialog = False, to preserve info between sessions
def run_iterpanda_experiment(task, background_knowledge=None):
    from .panda_agent import run_panda	# delayed import, to avoid circularity
    result, report_pathstem, report_summary, token_counts = \
        run_panda(task, background_knowledge=background_knowledge, reset_namespace=False, reset_dialog=False, force_report=True, allow_shortcuts=ALLOW_SHORTCUTS)
    return result, report_pathstem, report_summary

def simulate_iterpanda_experiment(task, background_knowledge=None):
    
    background_knowledge_text = f"First consider the following background knowledge:\n" + background_knowledge if background_knowledge else ""
    prompt = f'''INSTRUCTION: Write a short, plausible, imaginary report, in plain text, summarizing research into the following task:
Task: {task}

In the report, include a failure analysis in which you identify one or two hypothetical categories where performance was unusually poor.
Try to make the report, including its findings, as realistic as possible.
Write your report in plain text format.'''
    simulator_model = 'gpt4'
    print(prompt)
    report_text = call_llm(background_knowledge_text + prompt, model=simulator_model)		# note background_knowledge_text is used, but not recorded in the history
    # fake print_so_far
    result_text = f"\n====================  {simulator_model} ====================\n" + report_text
    print(result_text)

    # Let's switch to a new directory for a new run:
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(agent_config.ROOT_DIR, "output", "experiment-"+now_str)
    os.makedirs(output_dir, exist_ok=True)
    report_pathstem = os.path.abspath(os.path.join(output_dir,"experiment"))
    with open(report_pathstem+".txt", 'w', encoding="utf-8", errors='ignore') as f:
        f.write(report_text)    

    result = "done"		# flag report was successful!
    report_summary = call_llm("Generate one or two sentences that briefly summarize the conclusions of this research:\n\n"+report_text)

    return result, report_pathstem, report_summary

# ======================================================================

def collect_experiments_trace(logbook=None):
    """
    loop through the log file, find expt numbers + trace file locations
    read the trace files and assemble into a single string with appropriate headers
    return that string, and the number of the last experiment
    """
    traces_data = extract_experiments_traces(logbook)
    experiments_trace = ""
    experiment_number = 0
    for trace_data in traces_data:
        experiment_number = trace_data['experiment_number']
        trace_file = trace_data['trace_file']
        with open(trace_file, 'r', encoding='utf-8', errors='ignore') as f:
            trace = f.read()
        trace_header = f"""            

======================================================================
		EXPERIMENT {experiment_number}
======================================================================

"""
        experiments_trace += trace_header + trace

    print(f"DEBUG: Found {experiment_number} experiments in the log file so far...")        
    return experiments_trace, experiment_number		# experiment_number is the LAST experiment

# ----------

"""
Extract all EXPERIMENT lines like:
  EXPERIMENT 1 (....<a href="c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt">trace</a>)
  EXPERIMENT 1 ([report](...), [trace](c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt))
to return a LIST of dicts:
  {"experiment_number":1, "trace":"c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt")
"""
def extract_experiments_traces(logbook):
# Pattern for HTML    
#   pattern = re.compile(
#       r'EXPERIMENT\s+(\d+)\s*\(.*?<a href="([^"]+?experiment-trace\.txt)"[^>]*>trace</a>',
#       re.IGNORECASE | re.DOTALL
#   )
# Pattern for MD format    
    pattern = re.compile(
        r'EXPERIMENT\s+(\d+)\s*\(.*?\[trace\]\(([^)]+)\)',
        re.IGNORECASE | re.DOTALL
    )
    results = []
    for match in pattern.finditer(logbook):
        n = int(match.group(1))
        trace_path = match.group(2)
        results.append({"experiment_number": n, "trace_file": trace_path})
    return results

# ======================================================================
#	QUERY FOR THE NEXT ACTION
# ======================================================================    

# -> return best_next_task {"task_number":..., "task":, "rationale":...}, explanation
# iterpanda_dialog has already been set to: [MAIN_INTRO + PART_ONE_HEADER + experiments_trace + PART_TWO_HEADER + logbook]
def get_task_recommendations():
    global iterpanda_dialog
    prompt = """
Now go ahead and suggest possible follow-on research tasks that I might persue, based on these results,
that would contribute to my mission. Return your ideas using the following JSON structure:

  {"possible_next_tasks": [TASK1,TASK2,...]}

Where a TASK has the structure {"task_number":INTEGER, "task":DESCRIPTION, "rationale":RATIONALE}, i.e. return:

  {"possible_next_tasks": [{"task_number":1, "task":DESCRIPTION1, "rationale":RATIONALE1}, {"task_number":2, ...}, ..., ...]}

where:
  task_number: An integer to index the task (1, 2, ...)
  task: The new task that you're proposing (a string)
  rationale: Describe how the new task follows from the prior work, and how it might contribute to my overall mission (a string)

Propose between 1 and 5 tasks - make sure you propose AT LEAST one!

Go ahead!"""
    iterpanda_dialog.append(prompt)
    my_print("\n<experiments_trace + logbook>\n" + prompt, 'IterPanda')
    response_json, response_str  = call_llm_json(iterpanda_dialog, response_format=PossibleNextTasks, model=agent_config.ITERPANDA_LLM)
    my_print(response_str, agent_config.ITERPANDA_LLM)
    iterpanda_dialog.append(response_str)    
    possible_next_tasks = response_json['possible_next_tasks']

    prompt2 = f"""
Now, based on the original mission, which of those tasks that you just suggested should I research next, i.e., which is likely to contribute MOST to my mission?
Return your answer as a JSON of the form:
    {{"best_next_task_number":INTEGER, "rationale":RATIONALE}}
"""
    my_print(prompt2, 'IterPanda')
    iterpanda_dialog.append(prompt2)
    response_json, response_str  = call_llm_json(iterpanda_dialog, response_format=SelectedTask, model=agent_config.ITERPANDA_LLM)
    my_print(response_str, agent_config.ITERPANDA_LLM)        
    iterpanda_dialog.append(response_str)

    best_next_task_number = response_json['best_next_task_number']
    rationale = response_json['rationale']

    next_task_json = None
    for possible_next_task in possible_next_tasks:
        if possible_next_task.get("task_number") == best_next_task_number:
            next_task_json = possible_next_task

    best_next_task = next_task_json['task']
    best_next_task_rationale = next_task_json['rationale']
    
    task_recommendations = "\n#### Possible next tasks:\n"
    for possible_next_task in possible_next_tasks:
        task_number = possible_next_task['task_number']
        task = possible_next_task['task']
        rationale = possible_next_task['rationale']
        task_recommendations += f"{task_number}. **Task**: {task} **Rationale**: {rationale}\n"

    task_recommendations += f"""\n**Recommendation for next task:**
**NEXT TASK:** Task number {best_next_task_number}: {best_next_task}
**Rationale** {best_next_task_rationale}\n"""
        
    return task_recommendations		# string in MD format

# ----------

def get_next_task(logbook):
    marker = "NEXT TASK"
    # Find the last occurrence of the marker
    last_idx = logbook.rfind(marker)
    if last_idx == -1:				# no NEXT TASK, so ask GPT to think of one instead
        print("DEBUG: No NEXT TASK found in logbook, so asking GPT for one...")
        return compute_next_task()
    # Extract everything from the last marker to the end
    next_task = logbook[last_idx + len(marker):].lstrip(string.punctuation + " ")	# strip "*: "
    print("DEBUG: Found NEXT TASK =", next_task)
    return next_task

def compute_next_task():
    global iterpanda_dialog
    prompt = """
Based on all this information, what task (experiment) do you recommend to do next, that would MOST contribute to my mission?
Return a description of the task that can be provided to the ASD system to pursue it. (Don't return a task number, return a task description)
"""
    iterpanda_dialog.append(prompt)
    my_print("<experiments_trace + logbook>\n\n" + prompt, 'IterPanda')
    response_str  = call_llm(iterpanda_dialog, model=agent_config.ITERPANDA_LLM)
    my_print(response_str, agent_config.ITERPANDA_LLM)
    iterpanda_dialog.append(response_str)    
    return response_str

# ----------

# Define JSON response structure for {"possible_next_tasks": [{"task_number":1, "task":DESCRIPTION1, "rationale":RATIONALE1}, {"task_number":2, ...}, ..., ...]}
class PossibleNextTasks (BaseModel):
    class PossibleNextTask(BaseModel):
        task_number:int
        task:str = Field(description="The new task that you're proposing")
        rationale:str = Field(description="Describe how the new task follows from the prior work, and how it might contribute to my overall mission")
    possible_next_tasks: list[PossibleNextTask]

# Define JSON response structure for {"best_next_task_number":INTEGER, "rationale":RATIONALE}
class SelectedTask(BaseModel):
    best_next_task_number:int
    rationale:str = Field(description="Describe why this task is the one that will contribute MOST to my mission")

# ----------

def my_print(text, role="?"):
    print(f"================================ {role} =================================")
    print(text)


    



    





    



             

 
