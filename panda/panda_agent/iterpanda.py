"""
panda.run_iterpanda(logbook_file="logbook.md")
panda.run_iterpanda(logbook_file="logbook.md", n_iterations=5)
panda.run_iterpanda(logbook_file="logbook-persuasion-gpt5-mini2.md", n_iterations=5)
panda.run_iterpanda(logbook_file="logbook-persuasion-claude.md", n_iterations=5)
panda.run_iterpanda(logbook_file="logbook-persuasion-gpt5-mini-round7.md", n_iterations=3)
panda.run_iterpanda(logbook_file="persuasion-experiments/logbook-persuasion-gpt5-mini-round7.md")

panda.run_iterpanda(logbook_file="../brittleness-experiments/logbook-brittleness-claude-round1.md", n_iterations=1)
panda.run_iterpanda(logbook_file="../bias-experiments/logbook-bias-round1.md", n_iterations=1)
panda.run_iterpanda(logbook_file="../../theorizer/html_output-small-45-theories/logbook-context.md", n_iterations=1)

The overall structure:

 - LogBook contains a summary of the research so far, including the mission and ending with the NEXT TASK to perform.
 - If user says "Your turn", then Iternora reads the NEXT TASK, does it, summarizes the results (with hyperlinks to the
   details) in the logbook, and proposes possible next tasks and a suggested NEXT TASK to do next.
 - Then the user can either edit the logfile, ask questions, or say "Your turn" and the system will go again.
   If the user asks a question, it's posed after the full experiments_trace in the context.
NOTE: Currently literature search is done manually by the user, rather than with a "NEXT TASK: Find related work" statement.
NOTE: Is more reliable to splice NEXT TASK from the logbook algorithmically rather than asking an LLM to guess a NEXT TASK
   (which the user wouldn't then get to vet)

1. logbook.md
-------------
The LogBook is free text, but is puncuated by machine-readable headers with the structure
         EXPERIMENT <n> (...<a href=...>trace</a>...)
and also the structure:
         NEXT TASK: <description>
The next task = the block from "NEXT TASK:" to the end of the logbook.

collect_experiments_trace(logbook):
  Return the concatenation of all the experiments traces as a giant string (reading the tracefiles from extract_experiments_tracefiles).
  Each experiment trace in the string has a clear "EXPERIMENT <n>" heading.
  Also return the N of the last experiment found.

    extract_experiments_tracefiles(logbook):
      extract the tracefiles of experiments from the logbook, by looking for the "EXPERIMENT <n> (...<a href=...>trace</a>...)" headers.
      and returns a list of [{"experiment_number":1,"tracefile":<path-to-trace-file.txt>}, ...].
     Note: only the trace filenames, not the traces themselves, are in the logbook.

get_task_recommendations():
  Prompt for "What task I do next?", and return a textblock containing a list of options and the recommended one ("NEXT TASK: ...").
  To actually extract the recommended one, add them to the logbook file (via add_to_end_of_file(task_recommendations, logbook_file))
  then call get_next_task(logbook, logbook_file)

get_next_task(logbook, logbook_file):
  Find the *last* suggested NEXT TASK in the logbook (from "NEXT TASK:" to the end of the logbook).
  If none, simply ask GPT "What should I do next?"

2. Executing one iteration (= performing one experiment)
--------------------------------------------------------
experiments_trace = "Here's what we've done so far" + the concatenation of all the experiments' traces.
  a. Is supplied as background_knowledge to run_panda for use (only) at the start of the conversational context.
  b. Initial iterpanda_dialog with the user = [experiments_trace+logbook]

Now: 
 2.1 call task = get_next_task(logbook, logbook_file) to get the next task from the logbook. (no LLM involved, unless no NEXT TASK present).
 2.2 run_panda(task, background_knowledge=experiments_trace)
     Note the background_knowledge isn't added to the new experiment trace
 2.3 add the trace to iterpanda_dialog and ask for a short summary for the logfile. So now iterpanada_dialog looks:
	[experiments_trace+logbook, experiment_trace + "summary?",summary_for_logbook]
 2.4 add an "EXPERIMENT n (<a href=...>tracefile</a>)
             <summary_for_logbook>"
     to the logbook.
 2.5 reread the logbook, ask GPT for next task recommendations and NEXT TASK, add to logbook. 
     iterpanda_dialog now looks:
        [experiments_trace+logbook, experiment_trace + "summary?",summary_for_logbook,"possible next tasks, and preferred one?","1..2..3..NEXT TASK:.."]
 2.6 Stop.
     Note if we rerun, iterpanda_dialog is rebuilt from scratch, not continued, and will include the new experiment trace.
    
======================================================================

Usage:
panda.run_iterpanda(logbook_file="logbook.md")
where logbook.md might start:
"# Research Mission
 How much does an in-context fact influence model behavior?"

Given a top-level Mission (and optional task):
0. Select the last NEXT TASK in the logbook (otherwise generate one with a simple prompt):
1. Do the task experiment
2. Summarize the experiment and add to the end of the logbook:
       summary of experiment + possible next tasks + suggested NEXT_TASK

Example Missions: 
 - I want to build the best tunable hypothesis generator 
 - I want to distill a rulebase articulating a LM's apparent ethical decision-making rules
 - I want to characterize how good my LM is at math

How the Iternora dialog_so_far is built up over time (saved as a single string iterpanda_trace.txt)
  iterpanda_dialog = [mission,"ok",task1 + execution_trace_inc_report + "possible next tasks?",<list>,"pick one",<choice>,"I did it, and here's the results" + execution_trace_inc_report]
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
from panda.utils import call_llm, call_llm_json, read_file_contents, clear_directory, copy_file, file_exists, multiline_input, logger

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
panda.run_iterpanda(logbook_file="logbook-instruction-following.md")
panda.run_iterpanda(logbook_file="logbook-persuasion.md")
"""
def run_iterpanda(logbook_file="logbook.md", model=agent_config.ITERPANDA_LLM, n_iterations=0):
    global iterpanda_dialog

    if agent_config.ITERPANDA_LLM != model:
        logger.info(f"Updating default IterPanda model to be {model}...")
        agent_config.ITERPANDA_LLM = model
    if agent_config.PANDA_LLM != model:
        logger.info(f"Updating default Panda model to be {model}...")
        agent_config.PANDA_LLM = model        

    # sanity check:
    os.chdir(agent_config.ROOT_DIR)			# make sure you're back at the top
    if not logbook_file or not file_exists(logbook_file):
        message = f"ERROR! No such logbook file '{logbook_file}'!"
        logger.info(message)
        raise ValueError(message)

    next_task_printed = False
    reset_iterpanda_dialog = True
    
    while True:		# iterate for ever
    
        # ----------------------------------------
        # STEP 1: Load logbook
        # ----------------------------------------
        with open(logbook_file, "r", encoding="utf-8", errors='ignore') as f:
            logbook = f.read()    

        # ----------------------------------------
        # STEP 2: Either do and log the NEXT TASK, or answer a question for the user
        # ----------------------------------------
        experiments_trace, last_experiment_number = collect_experiments_trace(logbook)
        if reset_iterpanda_dialog:		# =True at the start OR after any run_and_log_experiment()
            iterpanda_dialog = [MAIN_INTRO + PART_ONE_HEADER + experiments_trace + PART_TWO_HEADER + logbook]	# **RESET** iterpanda_dialog at each step
            reset_iterpanda_dialog = False

        task = get_next_task(logbook, logbook_file, n_iterations)
        if not next_task_printed:
            logger.info(f"Next task (from logbook):\n{task}")
            next_task_printed = True

        if n_iterations > 0:
            run_and_log_experiment(task, experiments_trace, last_experiment_number, logbook_file, model, n_iterations)
            reset_iterpanda_dialog = True
            n_iterations += -1
        else:
            question = multiline_input('\nEnter question, "doit" (next logbook task), "panda", or "q" to quit. End with blank line (**HIT RETURN TWICE**)\n> ')         
            if question.strip().lower() == "q":
                break					# break out of "while True" loop to ipython prompt
            if question.strip().lower() == "":
                pass
            elif question.strip().lower() in ["do it","doit"]:
                reset_iterpanda_dialog = True                
                n_iterations = 1					# redo from the top, so as to reread the log file
#               run_and_log_experiment(task, experiments_trace, last_experiment_number, logbook_file, model, n_iterations)
#               reset_iterpanda_dialog = True
                
            elif question.strip().lower() in ["panda"]:
                background_knowledge = """
==================== START OF WHAT WE'VE DONE TOGETHER SO FAR ====================
Here's what we've done together so far:
""" + experiments_trace + """
==================== END OF WHAT WE'VE DONE TOGETHER SO FAR ====================
"""
                report_result, report_pathstem, report_summary = run_iterpanda_experiment(task=None, background_knowledge=background_knowledge, force_report=False)
                logger.info("DEBUG: report_result = %s", report_result)
                logger.info("DEBUG: report_pathstem = %s", report_pathstem)
                logger.info("DEBUG: report_summary = %s", report_summary)

            else:
                iterpanda_dialog.append(question)
                logger.info(f"Thinking (with {model})...")
                answer = call_llm(iterpanda_dialog, model=agent_config.ITERPANDA_LLM)
                my_print(answer, agent_config.ITERPANDA_LLM)
                iterpanda_dialog.append(answer)

# ------------------------------        

def run_and_log_experiment(task, experiments_trace, last_experiment_number, logbook_file, model, n_iterations):
    global iterpanda_dialog
    
    background_knowledge = """
==================== START OF WHAT WE'VE DONE TOGETHER SO FAR ====================
Here's what we've done together so far:
""" + experiments_trace + """
==================== END OF WHAT WE'VE DONE TOGETHER SO FAR ====================
"""
    report_result, report_pathstem, report_summary = run_iterpanda_experiment(task, background_knowledge=background_knowledge, model=model)
    logger.info("DEBUG: report_result = %s", report_result)
    logger.info("DEBUG: report_pathstem = %s", report_pathstem)
    logger.info("DEBUG: report_summary = %s", report_summary)

    experiment_trace = my_globals.print_so_far		# *excudes* SYSTEM_PROMPT + background_knowledge, so we don't double up. This content is stored in "...-trace.txt" in the experiment's directory

    # ----------------------------------------
    # STEP 3: Generate a summary of the experiment for the logbook
    # ----------------------------------------    

    prompt_for_summary = """
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

    trace_plus_prompt_for_summary = "Thanks! Ok, I've taken your advice and performed this new experiment. The results are as follows:\n" + experiment_trace + prompt_for_summary

    my_print(prompt_for_summary, 'IterPanda')	# don't print out the trace again for the user (already is visible)
    iterpanda_dialog.append(trace_plus_prompt_for_summary)
    experiment_summary  = call_llm(iterpanda_dialog, model=agent_config.ITERPANDA_LLM)
    my_print(experiment_summary, agent_config.ITERPANDA_LLM)
    iterpanda_dialog.append(experiment_summary)    

# HTML version
#   report_href = f'<a href="{report_pathstem}.txt">report</a>, ' if file_exists(f"{report_pathstem}.txt") else ""    
#   code_href = f'<a href="{report_pathstem}.py">code</a>, ' if file_exists(f"{report_pathstem}.py") else ""
#   artifacts_href = f'<a href="{report_pathstem}-artifacts.py">artifacts</a>, ' if file_exists(f"{report_pathstem}-artifacts.py") else ""
#   trace_href = f'<a href="{report_pathstem}-trace.txt">trace</a>'
#   file_hrefs = "(" + report_href + code_href + artifacts_href + trace_href + ")"

# MD version
    report_html_href = f"[report (html)]({report_pathstem}.html), " if file_exists(f"{report_pathstem}.html") else ""	# switched to HTML
    report_txt_href = f"[report (txt)]({report_pathstem}.txt), " if file_exists(f"{report_pathstem}.txt") else ""	# later: add TXT also
    code_href = f"[code]({report_pathstem}.py), " if file_exists(f"{report_pathstem}.py") else ""
    artifacts_href = f"[artifacts]({report_pathstem}-artifacts.py), " if file_exists(f"{report_pathstem}-artifacts.py") else ""
    trace_href = f"[trace]({report_pathstem}-trace.txt)"
    file_hrefs = "(" + report_txt_href + report_html_href + code_href + artifacts_href + trace_href + ")"

    logbook_entry = DASHES + f"EXPERIMENT {str(last_experiment_number+1)} {file_hrefs}\n------------\n" + "- **Task Description:**" + task + "\n" + experiment_summary
    add_to_end_of_file(logbook_entry, logbook_file)		# Extend the logbook    

    # ----------------------------------------
    # STEP 4: Generate some recommendations for next steps
    # ----------------------------------------

    # reread the updated logbook and experiments
    with open(logbook_file, "r", encoding="utf-8", errors='ignore') as f:
        logbook = f.read()
    experiments_trace, last_experiment_number = collect_experiments_trace(logbook)         

    task_recommendations = get_task_recommendations(n_iterations=n_iterations)
    add_to_end_of_file(task_recommendations, logbook_file)		# Extend the logbook        

#------------------------------

def add_to_end_of_file(string, file):
    with open(file, "a", encoding="utf-8", errors='ignore') as file:
        file.write(string)

# ======================================================================
#	RUN THE ACTUAL EXPERIMENT
# ======================================================================        

# [1] NOTE: reset_namespace, reset_dialog = False, to preserve info between sessions, so new session can use variables from prior sessions. But do we really care about this?
#     BUT: Then the dialog history from the PREVIOUS session is included to write the report = BAD! And experiment-trace-long.txt includes the trace from the PREVIOUS session
#          Not a good idea. Really reset_dialog=False should only be set to continue the CURRENT experiment
def run_iterpanda_experiment(task, background_knowledge=None, model=agent_config.ITERPANDA_LLM, force_report=True):
    from .panda_agent import run_panda	# delayed import, to avoid circularity
    result = run_panda(task, background_knowledge=background_knowledge, force_report=True, allow_shortcuts=ALLOW_SHORTCUTS, model=model, outputs_dir="output_iterpanda")
    
# TEMP PATCH
# result = {'result_flag':'done', 'report_pathstem':'c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output_iterpanda/experiment-20251021-135153/experiment', 'summary':'''This comprehensive analysis of 48 political questions across 6 dimensions definitively demonstrates that Claude 3.5 exhibits systematic liberal bias, with 100% of responses scoring as liberal-leaning (mean score -11.1 on a -10 to +10 scale) and zero neutral or conservative responses detected. The bias is extreme in magnitude, highly consistent across all political dimensions, and statistically significant (p < 0.001), with the strongest liberal positions appearing on environmental policy and social issues.''', 'token_counts':[{'model': 'claude-sonnet-4-20250514', 'prompt_tokens': 1642543, 'completion_tokens': 87210, 'total_tokens': 1729753}, {'model': 'claude-3-5-sonnet-20240620', 'prompt_tokens': 2440, 'completion_tokens': 25403, 'total_tokens': 27843}, {'model': 'gpt-4.1', 'prompt_tokens': 35001, 'completion_tokens': 8348, 'total_tokens': 43349}]}

    result_flag, report_pathstem, summary, token_counts = result["result_flag"], result["report_pathstem"], result["summary"], result["token_counts"]            
# [1]   run_panda(task, background_knowledge=background_knowledge, reset_namespace=False, reset_dialog=False, force_report=force_report, allow_shortcuts=ALLOW_SHORTCUTS, model=model, outputs_dir="output_iterpanda")
    return result_flag, report_pathstem, summary

"""
##### SIMULATION: No longer used
def run_iterpanda_experiment(task, background_knowledge=None, model=agent_config.ITERPANDA_LLM):
    
    background_knowledge_text = f"First consider the following background knowledge:\n" + background_knowledge if background_knowledge else ""
    prompt = f'''INSTRUCTION: Write a short, plausible, imaginary report, in plain text, summarizing research into the following task:
Task: {task}

In the report, include a failure analysis in which you identify one or two hypothetical categories where performance was unusually poor.
Try to make the report, including its findings, as realistic as possible.
Write your report in plain text format.'''
    simulator_model = 'gpt4'
    logger.info(prompt)
    report_text = call_llm(background_knowledge_text + prompt, model=simulator_model)		# note background_knowledge_text is used, but not recorded in the history
    # fake print_so_far
    result_text = f"\n====================  {simulator_model} ====================\n" + report_text
    logger.info(result_text)

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
"""

# ======================================================================

def collect_experiments_trace(logbook=None):
    """
    loop through the log file, find expt numbers + trace file locations
    read the trace files and assemble into a single string with appropriate headers
    return that string, and the number of the last experiment
    """
    tracefiles_data = extract_experiments_tracefiles(logbook)
    experiments_trace = ""
    experiment_number = 0
    for trace_data in tracefiles_data:
        tracefile = trace_data['tracefile']
        experiment_number = trace_data['experiment_number']
        try:
            with open(tracefile, 'r', encoding='utf-8', errors='ignore') as f:
                trace = f.read()
        except Exception as e:
            trace = f"ERROR! Couldn't find trace file {tracefile}."
            logger.info(trace)
            
        trace_header = f"""            

======================================================================
		EXPERIMENT {experiment_number}
======================================================================

"""
        experiments_trace += trace_header + trace

    logger.info(f"DEBUG: Found {experiment_number} completed experiment(s) in the log file so far...")        
    return experiments_trace, experiment_number		# experiment_number is the LAST experiment

# ----------

"""
Extract all EXPERIMENT lines like:
  EXPERIMENT 1 (....<a href="c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt">trace</a>)
  EXPERIMENT 1 ([report](...), [trace](c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt))
to return a LIST of dicts:
  {"experiment_number":1, "tracefile":"c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/output/experiment-20250706-121927/experiment-trace.txt")
"""
def extract_experiments_tracefiles(logbook):
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
        results.append({"experiment_number": n, "tracefile": trace_path})
    return results

# ======================================================================
#	QUERY FOR THE NEXT ACTION
# ======================================================================    

# Prompt for "What task I do next?", and return a textblock containing a list of options and the recommended one ("NEXT TASK: ...").
# iterpanda_dialog has already been set to: [MAIN_INTRO + PART_ONE_HEADER + experiments_trace + PART_TWO_HEADER + logbook]
def get_task_recommendations(n_iterations=0):
    global iterpanda_dialog

### No, we'll assume user continues to act even after this
#    if n_iterations == 0:			# no iterations
#        iteration_message = ""
#    elif n_iterations == 1:
#        iteration_message = "Note: This is the LAST iteration of experimentation, so propose possible final research tasks that will lead to a clear, final conclusion."
#    else:
#        iteration_message = f"Note: There are only {n_iterations} iteration(s) of experiments left, so plan ahead and propose possible research tasks that will help lead to a clear, final conclusion."
    iteration_message = ""

    prompt = f"""
Now go ahead and suggest possible follow-on research tasks that I might persue, based on these results, that would contribute to my mission. 
{iteration_message}
""" + """
Return your ideas using the following JSON structure:

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

# returns: the chunk of text (string) in logbook from the *last* NEXT TASK marker to the end of the logbook file.
# If none, ask GPT a simple query "What should I do next?" to generate a next-task string.
def get_next_task(logbook, logbook_file, n_iterations):
    marker = "NEXT TASK"
    # Find the last occurrence of the marker
    last_idx = logbook.rfind(marker)
    if last_idx == -1:				# no NEXT TASK, so ask GPT to think of one instead
        logger.info("DEBUG: No NEXT TASK found in logbook, so asking GPT for one...")
        task_recommendations = get_task_recommendations(n_iterations)
        add_to_end_of_file(task_recommendations, logbook_file)		# Extend the logbook
        logbook += task_recommendations
        return get_next_task(logbook, logbook_file, n_iterations)	# loop back and try again with the extended logbook
    # Extract everything from the last marker to the end
    next_task = logbook[last_idx + len(marker):].lstrip(string.punctuation + " ")	# strip "*: "
    return next_task


# PEC: This is now folded into get_task_recommendations() see prompt2
#def generate_next_task():
#    global iterpanda_dialog
#    prompt = """
#Based on all this information, what task (experiment) do you recommend to do next, that would MOST contribute to my mission?
#Return a description of the task that can be provided to the ASD system to pursue it. (Don't return a task number, return a task description as a string)
#"""
#    iterpanda_dialog.append(prompt)
#    my_print("<experiments_trace + logbook>\n\n" + prompt, 'IterPanda')
#    response_str  = call_llm(iterpanda_dialog, model=agent_config.ITERPANDA_LLM)
#    my_print(response_str, agent_config.ITERPANDA_LLM)
#    iterpanda_dialog.append(response_str)    
#    return response_str

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
    logger.info(f"================================ {role} =================================")
    logger.info(text)


    



    





    



             

 
