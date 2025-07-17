
"""
USAGE:
%load_ext autoreload
%autoreload 2 
import panda

panda.run_panda()				# interactive
panda.run_panda(task="How good is Llama at 2-digit addition?",allow_shortcuts=True)    # batch run

Also:
panda.run_panda(plan=['Generate 5 math questions','Have Llama answer them','Score the answers','Ensure the variance in the scores is > 0.5'])

### Running a santity test. Note this takes 30-60 mins to complete
panda.test_panda()
panda.evaluate()		# in panda/evaluate

Sketch of a statistical significance calculation: https://gemini.google.com/app/f977a458ba34a68f - see the end, not the start

Tracking:
my_globals.print_so_far = what the user sees as printed by print_to_user (abbreviated trace)
my_globals.dialog_so_far = GPT dialog (list)
observation(s) - what gets added to prompt, which gets added to my_globals.dialog_so_far. Some (but not all) are print_to_user'ed also.

NEW: run_panda() creates a subdirectory "output/experiment-<timestamp>/" and puts all created files in that subdirectory as follows:
   experiment.txt		# report
   experiment.html		# report
   experiment.py		# code
   experiment-artifacts.py	# artifacts (vars and dataframes)
   experiment-trace.txt		# short trace (what user sees)
   experiment-trace-long.txt	# full dialog with GPT
Occasionally Panda will output additional files (.csv, plots) to this directory also during code execution.   
The stem "experiment" is currently hardwired.
"""

import json
import pandas as pd
import time
import datetime
import os
import traceback
import requests
from func_timeout import func_timeout, FunctionTimedOut
from string import Template		# for build_system_prompt()

# fix to avoid "RuntimeError: main thread is not in main loop" during generated code execution (can't run interactive plt in func_timeout()
# https://chatgpt.com/share/68558c31-646c-8001-b00c-56adbe12ad15
import matplotlib
matplotlib.use('Agg')  # must be done before importing pyplot
import matplotlib.pyplot as plt

# for redirecting output
import io
import sys
import re
from contextlib import redirect_stdout, redirect_stderr

# import counters and constants
from . import my_globals         # leave "my_globals." prefix on globals for now, for clarity
from . import config as agent_config

# import prompts
from .panda_agent_subprompts import *

### These are the TOOLS available to Panda for research (for now)
from panda.researchworld import create_dataset, answer_questions, score_answers, spearman_strength, pearson_strength, ideate_categories, examples_in_category
from panda.researchworld import get_function_documentation, get_workflow_documentation, get_plan_documentation
from panda.utils import call_llm, llm_list, get_token_counts
from .report_writer import write_report, REPORT_DIR

# Below purely to get researchworld.tools.created_datasets and researchworld.tools.created_categories vars (rather than a COPY of those vars at import time, voa from ... import ..)
import panda.researchworld.tools as tools
import panda.researchworld.ideate_categories as ideate_categories

### Additional functions used by the Panda agent implementation itself (but not required to do research)
from panda.utils import call_llm, call_llm_json, parse_code, multiline_input, similar_strings, reset_token_counts, printf
from .report_writer import save_dialog

from panda.researchworld.lit_search import *	# lit tasks - not yet included
from panda.researchworld.lit_ideation import *

from .superpanda import run_superpanda
from .iterpanda import run_iterpanda

# ----------------------------------------

# Cosmetic preferences:
sys.stdout.reconfigure(encoding='utf-8')                # occasionally GPT can return a non-standard character, which raises an exception when I attempt to print it (stdout) 
pd.set_option('display.float_format', '{:.6f}'.format)  # avoid printing in exponent format
pd.set_option('display.width', 200)

# prettier displaying of DataFrames
pd.set_option('display.max_rows', 10)
pd.set_option('display.max_columns', 10)
pd.set_option('display.max_colwidth', 500)

# Globals - also see others in my_globals.py that are shared across multiple files
retry_counter = 0
retry_earlier_step_counter = 0
plot_counter = 0
interactive = False
nora_thread_id = None		# for use with the NORA UI
nora_system_output = ""         # for use with the NORA UI

SYSTEM_PROMPT = None		# built at runtime with build_system_prompt()
ADVICE = None
#USE_ADVICE = True
USE_ADVICE = False

# ----------

# Last step in a partial plan
LAST_PARTIAL_PLAN_STEP = "Plan what to do next"
TEST_TASKS = ["How good is OLMo at 2-digit addition, e.g., '23 + 43 = ?'", \
              "How well can OLMo translate into different languages?", \
              "Is Olmo or Llama better at telling jokes?", \
              "How well correlated are OLMo's and Llama's abilities at math?"]

# "unit tests" - These are examples in the prompt, so better be able to do these at least!
def test_panda():
    result_summaries = ""
    for test_task in TEST_TASKS:
        result = run_panda(task=test_task)
        result_summary = f"FINAL result: {result} for task: {test_task}."
        print_to_user(result_summary)
        result_summaries += result_summary + "\n"
    print_to_user("\n\nFINAL RESULTS:\n", result_summaries)        

# ----------        

# State class, to store variables
class State:
    def __init__(self, iteration=0, observations="", namespace=None):
        self.iteration = iteration
        self.observations = observations
        self.namespace = namespace or {}

"""
======================================================================
		MAIN FUNCTION: run_panda()
======================================================================
background_knowledge = contextual text to provide at the start of the conversation. It doesn't reappear later (unlike the task which is repeated)
force_report = True: Write a report for *successful* (result='done') research (sometimes the plan might omit report-writing)
allow_shortcuts = True: Don't check for hallucinations/shortcuts in the research, and don't give option to abort (except for too many iterations)

Core functions. Two modes:
1. Interactive: task=None, interactive=True - repeatedly ask for the next task
2. Non-intearctive: task=task, interactive=False - do the given task then stop. Returns "success" or "fail" depending on the outcome
RETURNS: 
 - result ("done" or an error code)
 - the filestem of a report (if one was generated)
If a report wasn't generated, and you want one, call write_report() which return a filestem

"""
def run_panda(task=None, plan=None, background_knowledge=None, force_report=False, thread_id=None, reset_namespace=True, allow_shortcuts=False, model=agent_config.PANDA_LLM, reset_dialog=True):

    # Let's switch to a new directory for a new run:
    now_str = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = os.path.join(agent_config.ROOT_DIR, "output", "experiment-"+now_str)
    os.makedirs(output_dir, exist_ok=True)
    os.chdir(output_dir)

    global interactive, nora_thread_id, nora_system_output
    print_to_user(agent_config.VERSION, " (running using ", model, ")", sep="")
    agent_config.PANDA_LLM = model

    if reset_namespace or not hasattr(my_globals, 'state') or not my_globals.state:		# make sure my_globals.state has some initial value
        state = reset_the_namespace()
    else:
        state = my_globals.state['state']    	# continue from last time

    if reset_dialog or not SYSTEM_PROMPT:
        reset_the_dialog(task=task, background_knowledge=background_knowledge, allow_shortcuts=allow_shortcuts)

    reset_panda_session()		# always do this - reset all counters        
    nora_thread_id = thread_id		# for use with the NORA UI
    nora_system_output = ""		# for use with the NORA UI
    summary_str = ""
    interactive = False if task else True

    try:
        if plan:	# e.g., ["eat","drink"].   Can optionally specify task too
            structured_plan = []
            for step_number, step in enumerate(plan):
                structured_plan.append({'step_number':step_number+1, 'step':step})
            planinfo = {'plan':structured_plan, 'step_number':1, 'step':plan[0]}
            if task is None:				# can optionally specify
                task = 'Execute the plan'
            task_plan = [{'step_number':1,'step':task}]
            task_planinfo = {'plan':task_plan, 'step_number':1, 'step':task}	
            result = panda_step("act", planinfo, state, [task_planinfo], model)	# MAIN ENTRY POINT
        
        elif task:
#	   No, might be too big!            
#          if background_knowledge:
#               print_to_user("Background knowledge:", background_knowledge)		       # We kind-of need to see this, even if it's big!
            print_to_user("Top-Level Task:", task)
            plan = [{'step_number':1,'step':task}]			       # The top-level task is treated as a "plan" with 1 step = the entire task.
            planinfo = {'plan':plan, 'step_number':1, 'step':task}	       # planinfo = the plan, plus a note of the current step (initially = 1).
            result = panda_step("strategize", planinfo, state, [], model)  # strategize = decide whether to plan, or just do the task (if simple).    MAIN ENTRY POINT

        else:
            planinfo = {'plan':None, 'step_number':None, 'step':None}
            result = panda_step("start", planinfo, state, [], model)			# MAIN ENTRY POINT. result = "done" or "abort_<failure mode>"

        # If already wrote report as part of the plan, then return that one. Else write a report (if research successful ("done")).
        report_pathstem = my_globals.last_report_pathstem
        if not file_exists(report_pathstem + ".txt") and force_report and result == "done":
            try:
                message = "No report generated! Trying to generate one now...\n"
                print_to_user(message)
                my_globals.dialog_so_far[-1] += message
                write_report()
            except Exception as e:
                tb = traceback.format_exc()                             
                message = f"Error writing report: {e}\nTraceback:\n{tb}\nCreated a dummy report....(NOTE timestamp may not perfectly match save_dialog() files...)\n"
                print_to_user(message)
                my_globals.dialog_so_far[-1] += message
                with open(report_pathstem + ".txt", "w", encoding='utf-8', errors='replace') as file:
                    file.write(message)

        # Now tidy up
        summary_str = get_summary(result)
        message = "\n-------------------------------------\nFinal summary: " + summary_str + "\n"
        print_to_user(message)
        my_globals.dialog_so_far[-1] += message            
    
        if not interactive:        
            save_dialog()	

    except Exception as e:
        tb = traceback.format_exc()                                     
        message = f"Yikes! Top-level run_panda() failed!! Error: {e}\nTraceback:\n{tb}\n"
        print_to_user(message)
        my_globals.dialog_so_far[-1] += message        
        result = "abort_python_error"
        report_pathstem = None
        summary_str = message

    token_counts = get_token_counts()		# in utils/ask-llm.py  eg [{"model":"gpt-4.1","prompt_tokens":100,"completion_tokens":310,"total_tokens":410}]
    os.chdir(agent_config.ROOT_DIR)		# make sure you're back at the top
    
    print(f"DEBUG: run_panda(): result = {result}, report_pathstem = {report_pathstem}, summary_str = {summary_str}, token_counts = {token_counts}")
    return result, report_pathstem, summary_str, token_counts

# ----------

# Summarize the research trajectory (used only for NORA UI).
# (Note the outcome could be an abort).
# I need to add the prompt as a NEW element (+[prompt]) otherwise it potentially gets concatenated (and hence confused with) to the earlier instructions.
def get_summary(result):
    if result == "done":
        prompt = "Generate one or two sentences that briefly summarize the conclusions of this research."
    else:
        prompt = f"The research failed to to an error ({result}). Generate one or two sentences briefly summarizing what went wrong."
        
    summary_str = call_llm(my_globals.dialog_so_far + [prompt], model=agent_config.PANDA_LLM)
    print("DEBUG: Final summary:", summary_str)
    return summary_str

#def get_summary():
#    prompt = "\n\nFinally, Generate one or two sentences that briefly summarize the conclusions of this research."
#    my_globals.dialog_so_far[-1] += prompt				# this APPENDS prompt to the last string (= observations) in the list
#    summary_str = call_llm(my_globals.dialog_so_far, model=agent_config.PANDA_LLM)
#    my_globals.dialog_so_far.append(summary_str)
#    print("Final summary:", summary_str)
#    return summary_str

# ----------

def reset_the_dialog(task=None, background_knowledge=None, allow_shortcuts=False):
    global SYSTEM_PROMPT, ADVICE    
    SYSTEM_PROMPT = build_system_prompt(allow_shortcuts=allow_shortcuts)
    if task:
            my_globals.dialog_so_far = [SYSTEM_PROMPT + task_intro(task,background_knowledge)]
    else:
        my_globals.dialog_so_far = [SYSTEM_PROMPT]

def reset_the_namespace():
    namespace = initialize_namespace()
    state = State(iteration=0, observations="", namespace=namespace)
    return state    

"""
def reset_panda_state(task=None, background_knowledge=None, allow_shortcuts=False, reset_dialog=True):
    global SYSTEM_PROMPT, ADVICE

    if reset_dialog:		# otherwise continue with existing my_globals.dialog_so_far
        SYSTEM_PROMPT = build_system_prompt(allow_shortcuts=allow_shortcuts)
        if task:
            my_globals.dialog_so_far = [SYSTEM_PROMPT + task_intro(task,background_knowledge)]
        else:
            my_globals.dialog_so_far = [SYSTEM_PROMPT]

    reset_panda_session()

    namespace = initialize_namespace()
    state = State(iteration=0, observations="", namespace=namespace)
    return state    
"""

def reset_panda_session():
    global ADVICE
    my_globals.print_so_far = ""            # What the user sees, used for the NORA UI and also save_dialog() for saving the short version
    my_globals.code_so_far = ""
    my_globals.plotfiles_so_far = []	    # Note we *don't* reset plot_counter to avoid collisions between different experiments (for now...later should move them)
    tools.created_datasets = []
    ideate_categories.created_categories = []
    my_globals.py_counter = 1
    my_globals.start_time = time.time()    
    reset_token_counts()
    my_globals.last_report_pathstem = os.path.abspath("experiment")		# NEW: report_pathstem is a CONSTANT now	
    global retry_counter, retry_earlier_step_counter
    retry_counter = 0
    retry_earlier_step_counter = 0
    if USE_ADVICE:        
        print("DEBUG: Reading advice file...")        
        ADVICE = read_advice_file(agent_config.ADVICE_FILE)

# ----------

# Build system prompt dynamically, to accomodate changing researchworld function documenntation and example workflows
def build_system_prompt(allow_shortcuts=False):
    global SYSTEM_PROMPT, REFLECTION_SUBPROMPT, PLAN_REFLECTION_SUBPROMPT
    print("DEBUG: Building system prompt...")

    if allow_shortcuts:
        system_prompt_template_file = agent_config.SYSTEM_PROMPT_TEMPLATE_FILE_ALLOW_SHORTCUTS
        REFLECTION_SUBPROMPT = REFLECTION_SUBPROMPT_ALLOW_SHORTCUTS
        PLAN_REFLECTION_SUBPROMPT = PLAN_REFLECTION_SUBPROMPT_ALLOW_SHORTCUTS        
    else:
        system_prompt_template_file = agent_config.SYSTEM_PROMPT_TEMPLATE_FILE
    
#   with open(agent_config.SYSTEM_PROMPT_TEMPLATE_FILE, 'r') as f:
    with open(system_prompt_template_file, 'r') as f:
        SYSTEM_PROMPT_TEMPLATE = f.read()
    system_prompt_template = Template(SYSTEM_PROMPT_TEMPLATE)
    
    function_documentation = get_function_documentation()		# in researchworld
    report_writing_documentation = agent_config.doc['write_report']
    workflow_documentation = get_workflow_documentation()		# in researchworld
    plan_documentation = get_plan_documentation()		# in researchworld

    # add in panda_agent function documentation
    all_function_documentation = function_documentation + "\n4. WRITING A REPORT\n-------------------\n" + report_writing_documentation

    prompt_parameters = {'function_documentation':all_function_documentation,
                         'workflow_documentation':workflow_documentation,
                         'plan_documentation':plan_documentation}
    SYSTEM_PROMPT = system_prompt_template.substitute(prompt_parameters)
    
    with open(agent_config.SYSTEM_PROMPT_FILE, "w") as file:		# save it to disk, purely for user's benefit
        file.write(SYSTEM_PROMPT)
    return SYSTEM_PROMPT        

# ----------

# Restart after an abort. Unlike panda(), this preserves the current state and namespace so we can continue with follow-on queries
def restart():
    global interactive
    mode = "done"
    planinfo = my_globals.state['planinfo']
    state = my_globals.state['state']
    planstack = my_globals.state['planstack']
    interactive = True
    panda_step(mode, planinfo, state, planstack, model=agent_config.PANDA_LLM)

# Execute a Python command in the Panda execution environment
def py(cmd):
    if isinstance(cmd, str):
        exec(cmd, my_globals.state['state'].namespace)
    else:
        print_to_user("ERROR! Please provide a string as an argument to py()!")

### ======================================================================
###		MAIN LOOP	
### ======================================================================
"""
plan = [{step_number:INT, step:STEP},{...},...]
planinfo = {plan:PLAN, step_number:INT, step:STEP}.
planstack = LIST of planinfo, if doing recursive plans (currently disabled, so will be at most 1 deep)

The arguments to panda_step encode the plan tree, but we don't store the outcome of completed steps (but we could). 
for reviewing the execution.
"""
def panda_step(mode, planinfo, state, planstack=[], model=agent_config.PANDA_LLM):
    plan = planinfo['plan']
    step_description = planinfo['step']
    step_number = planinfo['step_number']
    my_globals.state = {'planinfo':planinfo,'state':state,'planstack':planstack}			# Store a global copy of state, in case we interrupt and resatart

    # ----------------------------------------
    # 1. safety check to prevent runaway Panda
    # ----------------------------------------    
    if state.iteration > agent_config.MAX_ITERATIONS:
        observation = f"Yikes!!! Exceeded MAX_ITERATIONS ({agent_config.MAX_ITERATIONS}) steps! Giving up!"
        state.observations += observation
        print_to_user(observation)
        mode = "abort_iterations"			# and pass onto next clause below

    # ----------------------------------------        
    # 2. Finished! Pop the plan stack (if any), else ask the user for a new task (interactive mode), or return the final result
    # ----------------------------------------
    if mode in ["start", "done", "abort_iterations", "abort_shortcuts", "abort_impossible", "abort_beyond_capabilities", "abort_python_error"]:
        if interactive and (mode != "done" or planstack == []):		# planstack == [] means main task done, not just a subtask done. mode !=  "done" means the main task was aborted.
            if mode != "start":
                save_dialog()				# make a note of previous research
            my_globals.start_time = time.time()         # reset the clock for the next iteration
            reset_token_counts()                
            new_task = multiline_input("\nWhat is the next research action/task you'd like me to do (or 'q' to quit)? End with blank line (**HIT RETURN TWICE**) \n> ")         
            if new_task == 'q':
                my_globals.dialog_so_far.append(state.observations)
                return "done"				# no return value in interactive mode
            else:
                print_to_user(f"\nTop-Level Task: {new_task}\n")
                if new_task.lower().startswith("task: "): 	# Prepend "Task: " *forces* Panda to plan then act (typically unnecessary)
                    new_mode = "plan"
                    new_task = new_task[6:]
                if new_task.lower().startswith("action: "):	# Prepend "Action: " *forces* Panda to directly start coding (avoid generating a flowery plan)
                    new_mode = "act"
                    new_task = new_task[8:]			
                else:
                    new_mode = "strategize"				# Otherwise, let Panda decide itself whether a plan is needed or not
                plan = [{'step_number':1, 'step':new_task}]
                observation = "----------------------------------------\n     STARTING THE NEXT RESEARCH TASK\n----------------------------------------\n" 
                state.observations += observation
                new_planinfo = {'plan':plan, 'step_number':1, 'step':new_task}
                return panda_step(new_mode, new_planinfo, state, [], model)

        elif planstack == []:		# completion of top-level plan (with either success or failure)
            my_globals.dialog_so_far.append(state.observations)
            return mode			# one of "done", "abort_shortcuts", "abort_iterations", "abort_beyond_capabilities". This is the FINAL return

        elif mode == "done":		# completion of subplan, so pop and go to the next step of the super-plan.
            superplan = planstack[0]
            return panda_step("next_step", superplan, state, planstack[1:], model)

        else: # mode in ["abort_beyond_capabilities","abort_shortcuts","abort_impossible", "abort_python_error"] # failure of subplan, so (for now) pop and pass the failure back up to the super-plan.
            superplan = planstack[0]
            return panda_step(mode, superplan, state, planstack[1:], model)

    # ----------------------------------------
    # 3. completed a step! so go to the next step (if there is one) and strategize OR declare victory ("done")
    # ----------------------------------------    
    # a_s({plan:[1,2,3], step_number:1, mode:"next_step"}, state, [{plan:[A],s:1}]) -> a_s({plan:[1,2,3], step_number:2, mode:"strategize"}, state, [{plan:[A],s:1}])
    # a_s({plan:[1,2,3], step_number:3, mode:"next_step"}, state, [{plan:[A],s:1}]) -> a_s({plan:[1,2,3], step_number:3, mode:"done"}, state, [{plan:[A],s:1}])
    # 		-> a_s({plan:[A], step_number:1, mode:"next_step"}, state, []) -> triggers the == len(plan) below
    elif mode == "next_step":
        if step_number == len(plan):
            observation = "\nThat was the last step! Plan execution is complete.\n"
            state.observations += observation            
            return panda_step("done", planinfo, state, planstack, model)
        elif step_number < len(plan):
            planinfo['step_number'] = step_number + 1
            planinfo['step'] = plan_step(plan, step_number + 1)
#           return panda_step("strategize", planinfo, state, planstack, model)   # this includes considering recursively creating a subplan, but that's a bit overkill for now.
            return panda_step("act", planinfo, state, planstack, model) # simpler: Just go and do the next step! (don't overthink things...)
        else:
            raise ValueError("DEBUG: step_number >= len(plan)! This should be impossible!! (reflect() should not return new_mode='next_step' in this situation)")
        
    # ----------------------------------------
    # 4. The above handles bookkeeping about steps and plans. The below panda_step0 now switches to actually using GPT to do the actual work (act/reflect)
    # ----------------------------------------    
    else:
        try:
            return panda_step0(mode, planinfo, state, planstack, model)
        except Exception as e:
            tb = traceback.format_exc()             
            print(f"Yikes! Unexpected exception: {e}.\nTraceback:\n{tb}\nAborting...")
            return panda_step("abort_python_error", planinfo, state, planstack, model)


# ----------

# plan = [{'step_number':1, 'step':'Create dataset'}, {'step_number':2, 'step':'Answer the questions'}]
# plan_step(plan,2) # -> 'Answer the questions'
def plan_step(plan, step_number):
#    print("DEBUG: plan =", plan)
    return [step["step"] for step in plan if step["step_number"] == step_number][0]	# find the text for step_number    

# ======================================================================
#		MAIN CONTROL LOOP
# separate out this main control section, which executes the main act/reflect steps, for code simplicity
# ======================================================================

def panda_step0(mode, planinfo, state, planstack, model=agent_config.PANDA_LLM):

    state.iteration += 1		# update counter
    plan = planinfo['plan']
    step_description = planinfo['step']
    step_number = planinfo['step_number']
    
    # Create prompt for the next step, depending on the mode
    formatted_task_hierarchy = "\n" + format_task_hierarchy(planinfo, planstack) if mode != "reflect" else ""
    header, mode_prompt, comment = generate_header_and_prompt(mode, planinfo, state.iteration, model)	# what question (prompt) to ask GPT, depending on the current mode
    prompt = state.observations + formatted_task_hierarchy + header + mode_prompt		# pre-pend the observations from previous iteration to the prompt
    if len(plan) > 1:
        print_to_user(f"Step {step_number}: {step_description}")
    print_to_user(comment)

    my_globals.dialog_so_far.append(prompt)						# <- add the prompt (question to GPT) to dialog so far...
    if mode in ["replan","continue_plan"]:
        temperature = 0.7			# need to avoid regenerating the same plan each time
    else:
        temperature = 0

    # ========================================
    #     THE MAIN AGENT CALL TO THE LLM
    # ========================================        
    response_json, response_str = call_llm_json(my_globals.dialog_so_far, temperature=temperature, model=model) # <- ask GPT for its reply...
    my_globals.dialog_so_far.append(response_str)    					# <- add GPT's reply to the dialog so far...

    # Process based on the mode								# Now, process the reply appropriately, depending on what the question (mode) was...
    if mode == "strategize":			# stategize = for current step, should I plan, just do it, or generate a partial plan?
        new_mode, state.observations = strategize(response_json)
        return panda_step(new_mode, planinfo, state, planstack, model)
        
    elif mode in ["plan", "partial_plan", "replan", "continue_plan"]:
        subplan, state.observations = create_plan(response_json, mode=mode)
        if subplan == []:
            message = "ERROR! A zero-step plan was generated! Giving up..."
            print_to_user(message)
            raise ValueError(message)
        else: 
            first_substep = plan_step(subplan, 1)
            subplaninfo = {'plan':subplan, 'step_number':1, 'step':first_substep}
            if mode in ["plan", "partial_plan"]:
                return panda_step("reflect_on_plan", subplaninfo, state, [planinfo] + planstack, model) # push planinfo onto stack ([...,subplan,plan,task]) for "plan" or "partial_plan"
            else:
                return panda_step("reflect_on_plan", subplaninfo, state, planstack, model)		# discard planinfo for "replan" or "continue_plan"

    elif mode == "reflect_on_plan":
        new_mode, state.observations = reflect_on_plan(response_json)
        return panda_step(new_mode, planinfo, state, planstack, model)

# partial_plan option not currently used        
#   elif mode == "act" and step_description == LAST_PARTIAL_PLAN_STEP:		# Special case: A partial plan ends with LAST_PARTIAL_PLAN_STEP = "Plan what to do next"
#       return panda_step("continue_plan", planinfo, state, planstack, model)

    elif mode in ["act", "continue", "debug", "retry", "retry_earlier_step"]:
        action, think_observations = generate_action(response_json)		# i.e., write code...
        act_observations = execute_action(action, state.namespace)		# then execute it...
        state.observations = think_observations + act_observations
        return panda_step("reflect", planinfo, state, planstack, model)

    elif mode == "reflect":
        new_mode, state.observations, new_planinfo = reflect(response_json, planinfo)	# mode updated in reflect() based on the reflection result. plan might change too
        return panda_step(new_mode, new_planinfo, state, planstack, model)

    else:
        raise ValueError(f"Unrecognized mode '{mode}'")

# ----------

# splice_out("abcdefg", start="bc", end="f") -> "ag"
def splice_out(string, start, end):
    "Splices out the part of a string between (and including) two markers start and end"
    try:
        start_index = string.index(start)
        end_index = string.index(end) + len(end)
        return string[:start_index] + string[end_index:]
    except ValueError:
        return string    

### ======================================================================

# Pretty print the current plan
# x = {'plan': [{'step_number': 1, 'step': 'What is 1 + 1?'}], 'step_number': 1, 'step': 'What is 1 + 1?'}
# format_task_hierarchy(x, [])
def format_task_hierarchy(planinfo, planstack):
#   print("planinfo =", planinfo)
    formatted_task = ""
    sub = ""
    full_planstack = planstack[::-1] + [planinfo]	# reverse planstack, so now it is [task,plan,subplan,...]
    top_level_task = full_planstack[0]['step']		# represented as a plan of length 1
    output = "Top-Level Task: " + top_level_task + "\n"
    for info in full_planstack[1:]:         		# skip top-level task
        formatted_plan = pretty_plan(info['plan'], indent=3)
        output += f"Current {sub}Plan:\n" + formatted_plan + "\n"
        sub += "Sub"
        output += f"Current {sub}Task: " + info['step'] + " (step " + str(info['step_number']) + ")\n"
    return output + "\n"

# ----------

def initialize_namespace():
    """Initialize a clean execution namespace."""
    namespace = globals().copy()
    namespace["__builtins__"] = __builtins__
    return namespace

# ----------

# Add extra text at the INTRO to the conversation. background_knowledge only appears here, and not any time later.
def task_intro(task=None, background_knowledge=None):
    bars = """
======================================================================
======================================================================
"""
    background_knowledge_intro = f"""
Here is some background_knowledge for the research you are about to do:
{background_knowledge}
""" if background_knowledge else ""
    
    task_intro = f"""
NOW: Here is your top-level research task:
{task}
""" if task else ""

    return bars + background_knowledge_intro + task_intro + bars

# ----------

# The global vars (upper-cased) below are defined in panda_agent_subprompts.py
def generate_header_and_prompt(mode, planinfo, iteration, model):
#    print("DEBUG: generating prompt for mode =", mode, "planinfo =", planinfo)
    """Generate headers and prompts for planning modes."""
    step_description = planinfo['step']		# the current step
    step_number = planinfo['step_number']	# the current step number
    header = "-" * 40 + "\n"

    if mode == "strategize":
        header += f"#{iteration}. Strategize how to proceed\n"
        prompt = STRATEGY_SUBPROMPT
        comment = "Strategizing..."
    elif mode == "partial_plan":
        header += f"#{iteration}. Generate Partial Plan (Explore)\n"
        prompt = PARTIAL_PLAN_SUBPROMPT
        comment = "Generating a partial plan..."
    elif mode == "continue_plan":
        header += f"#{iteration}. Generate a Continuing Plan...\n"
        prompt = CONTINUE_PLAN_SUBPROMPT
        comment = "Generating a continuation of the plan..."
    elif mode == "plan":
        header += f"#{iteration}. Generate Initial Plan\n"
        prompt = PLAN_SUBPROMPT
        comment = "Planning..."
    elif mode == "reflect_on_plan":
        header += f"#{iteration}. Reflecting on the Plan\n"
        prompt = PLAN_REFLECTION_SUBPROMPT
        comment = "Reflecting..."
    elif mode == "replan":
        header += f"#{iteration}. Replan Task\n"
        prompt = REPLAN_SUBPROMPT
        comment = "Replanning..."                
    elif mode == "act":
        advice = get_advice(step_description)
        header += f"#{iteration}. Perform Step {step_number}: {step_description}\n"
        header += advice
        prompt = ACTION_SUBPROMPT
#       print("DEBUG: advice =", repr(advice))
        if advice not in ['','""','- ""','-',"- "]:		# blank advice forms
            print("DEBUG: repr(advice) =", repr(advice))
            comment = f"Found advice: {advice}\nCoding..."
        else:
            comment = "Coding..."                        
    elif mode == "continue":
        header += f"#{iteration}. Continue Step {step_number}\n"
        prompt = CONTINUE_SUBPROMPT
        comment = "Coding..."                                
    elif mode in ["debug", "retry"]:
        header += f"#{iteration}. An error occurred doing step {step_number}. Let's try and debug the problem and retry (retry number {retry_counter}).\n"
        prompt = DEBUG_SUBPROMPT
        comment = "Coding..."
    elif mode == "retry_earlier_step":
        header += f"#{iteration}. Step {step_number} failed, indicating a problem at an earlier step in the plan. Returning to retry that earlier step (earlier retry number {retry_earlier_step_counter}).\n"
        prompt = DEBUG_SUBPROMPT
        comment = "Coding..."                                                
    elif mode == "reflect":
        header += f"#{iteration}. Reflect on Step {step_number}\n"
        prompt = REFLECTION_SUBPROMPT
#       comment = f"(Using {model} for Panda)\nReflecting..."        
        comment = "Reflecting..."                                        
    header += "-" * 40 + "\n"
    return header, prompt, comment

def pretty_plan(plan, indent=0):
    formatted_plan = ""
    for step in plan:
        if 'step_number' in step and 'step' in step:
            formatted_plan += " " * indent + f"{step['step_number']}. {step['step']}\n"
        else:
            formatted_plan += " " * indent + f"[key error] {step}\n"
    return formatted_plan

"""
======================================================================
		MAIN EXECUTION OPERATIONS
======================================================================
GIVEN: GPT's JSON response to the current question (prompt) from Panda
DO: Process the response, e.g., execute code, etc.
  Note: any observations are NOT printed out here*, rather they are returned back to the main function.
        They will be incorporated at the start of the NEXT prompt to GPT.

* with the exception of code execution exec() responses, as we'd like to see these in real-time.
======================================================================
"""
def strategize(response_json):
    strategy = response_json.get("strategy")
    explanation = response_json.get("explanation")
    observations = f"\nStrategy: {strategy}\nExplanation: {explanation}\n\n----------------------------------------\n"
    # To do sometime: rename strategy to the "mode" ontology used in Panda
    if strategy == "do":
        new_mode = "act"
    elif strategy == "plan":
        new_mode = "plan"
    elif strategy == "explore":
        new_mode = "partial_plan"
    else:
        print_to_user(f"[comment] ERROR!! Unrecognized strategy '{strategy}', should be one of 'do', 'plan', 'explore'! Assuming 'plan' and continuing...")
        new_mode = "plan"
    return new_mode, observations

# --------------------

# Generate plan (or more precisely: extract plan from the JSON which GPT already created!)
# Returns plan = [{'step_number': 1, 'step': "Generate a dataset"}, {'step_number': 2, 'step': "..."}...]
# mode = plan|replan|partial_plan
def create_plan(response_json, mode):
#   print("DEBUG: create_plan: response_json =", response_json)
    plan = response_json['plan']	# plan = [{'step_number': 1, 'step': "Generate a dataset"}, {'step_number': 2, 'step': "..."}...]
    if mode == "partial_plan":
        last_step = plan[-1]
        last_step_number, last_step_description = last_step['step_number'], last_step['step']
        if not similar_strings(last_step_description, LAST_PARTIAL_PLAN_STEP):
            print_to_user(f'[comment] WARNING! Last step of a partial plan should be "{LAST_PARTIAL_PLAN_STEP}" but was instead "{last_step_description}"! Changing it...')
        plan[-1] = {'step_number':last_step_number, 'step':LAST_PARTIAL_PLAN_STEP}
    observations = ""
    print_to_user("Plan:\n", pretty_plan(plan, indent=3), sep="")
    return plan, observations

# --------------------

# Generate code (or more precisely: extract code from the JSON which GPT already created!)
def generate_action(response_json):
    thought, action = response_json.get("thought"), response_json.get("action")
    observations = agent_config.CODING_START + f"Thought: {thought}\nAction (code):\n{action}\n\n----------------------------------------\n\n"
    return action, observations

"""
 ======================================================================
      EXECUTING AN ACTION (Python Code) IN THE ENVIRONMENT
 ======================================================================
def execute_action(action:str, namespace:dict):
Purpose:
   This is the interface between the Panda agent and the external environment. Here the external environment 
   is a Python shell, with a set of useful Python functions (tools) pre-loaded into it.
Args: 
   action (str): an action (a string listing one or more Python commands) to be executed
   namespace (dict): The namespace of the Python environment where the commands are to be executed. Its initial
                     value is created by initialize_namespace(), then destructively updated here at each call to exec()
Returns:
   observations (str): The observations returned from the environment. These are then prepended to the next call to GPT in panda_step0.
Side effects:
   Namespace is destructively updated as a result of the code execution
   Also will pretty-print to the terminal, but this is purely cosmetic for the user's benefit
"""
def execute_action(action:str, namespace):
    global plot_counter
    observations = "I'll now execute the actions (code) you suggested...\n\n" + agent_config.PYTHON_START + "\n"
    print_to_user(agent_config.PYTHON_START)

    # parse the action into commands
    try:
        commands = parse_code(action)   # NB Each command not terminated with "\n"
#       code_to_record = action
        code_to_record = ""		# new - record all successful commands (rather than all fully successful codeblocks)
    except Exception as e:
        tb = traceback.format_exc() 
        observation = f"Error: Can't even parse the generated commands:\n----------\n{action}\n----------\nError: {e}\nTraceback:\n{tb}"
        print_to_user(observation, end="")
        observations += observation
        observation = agent_config.CODING_END
        print_to_user(observation, end="")
        observations += observation
        return observations

    # do the commands
    for command in commands:
#       command = command.replace("plt.show()", "plt.show(block=False)")		    # Stop plt.show() blocking execution
        if "plt.show()" in command:
            plot_counter += 1
            plotfile = f"plot{plot_counter}.png"
            my_globals.plotfiles_so_far += plotfile
            plot_save_command = f'plt.savefig("{plotfile}")'
            command = command.replace("plt.show()", plot_save_command)			    # Replace show with save
        
        command_line = f"In [{my_globals.py_counter}]: {command}"
        observations += command_line + "\n"         # note for dialog
        print_to_user(command_line)	   	    # print to user [1]
        my_globals.py_counter += 1                
                
        f = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        tee_stdout = Tee(original_stdout, f)  # Capture both stdout and stderr
        tee_stderr = Tee(original_stderr, f)
        try:
            with redirect_stdout(tee_stdout), redirect_stderr(tee_stderr):
                func_timeout(agent_config.EXEC_TIMEOUT, exec, args=(command, namespace))
                code_to_record += command + "\n"	# new: record all successful commands
        except FunctionTimedOut:			# FunctionTimedOut is a subclass of BaseException, not Exception, so need separate clause here
            with redirect_stdout(tee_stdout), redirect_stderr(tee_stderr):
                observation = f"Error: Timeout!! The code took more than the max {agent_config.EXEC_TIMEOUT} secs (infinite loop)? Aborting execution..."
                print_to_user(observation)
                observations += observation + "\n"
                code_to_record = "# The below command failed to execute (raised a TimeOut exception)\n" + add_hash_prefixes(command) + "\n"
        except Exception as e:
            # Write the error message to the same buffer
            with redirect_stdout(tee_stdout), redirect_stderr(tee_stderr):
                tb = traceback.format_exc()
                observation = f"Error: {e}\nTraceback:\n{tb}"      # Add traceback for more debugging info
                print_to_user(observation)
                observations += observation + "\n"
                code_to_record = f"# The below command failed to execute (raised a {e} exception)\n" + add_hash_prefixes(command) + "\n"
                break						# New: if there's an error, give up immediately rather than continuing...
        finally:
            observation = f.getvalue()
            my_globals.print_so_far += observation     # Normally this var is set via print_to_user(), but in this case the observation was already printed to TTY by exec() earlier, so don't reprint it
            if nora_thread_id:		   	   # for integration into Nora
                print_to_nora(observation)
            print_to_user()
            observations += observation + "\n"
    observation = agent_config.CODING_END
    my_globals.code_so_far += "\n# ----------\n" + code_to_record + "\n# ----------\n"
    print_to_user(observation, end="")
    observations += observation
    return observations

# utility
def timeout_handler(signum, frame):
    raise TimeoutError("Command execution timed out.")

# add_hash_prefixes("a\nb") -> "# a\n# b"
def add_hash_prefixes(string):
    return '\n'.join('# ' + line for line in string.splitlines())

# ======================================================================

def reflect_on_plan(response_json):
    doability = response_json.get("doable")
    explanation = response_json.get("explanation")
    
    if doability == "no":			# In THIS situations, we'd like to know what the problem it saw actually was!
        print_to_user(f"Thought: {explanation}")
        print_to_user("Stopping...")
        new_mode = "abort_beyond_capabilities"
    else:
        new_mode = "act"
        
    observations = f"\nDoable: {doability}\nExplanation: {explanation}\n\n----------------------------------------\n"
    return new_mode, observations

# --------------------

# planinfo = {'plan':[{'step_number':1,'step':'Get up'},{...},...], 'step_number':1, 'step':'Get up'}
# return new_mode, new_step_number, observations
def reflect(response_json, planinfo):
    
    global retry_counter, retry_earlier_step_counter
    step_number = planinfo['step_number']
    plan = planinfo['plan']

    thought = response_json.get("thought")
    task_complete = response_json.get("task_complete", False)
    current_step_complete = response_json.get("current_step_complete", False)
    software_bug = response_json.get("software_bug", False)        
    took_shortcuts = response_json.get("took_shortcuts", False)
    next_action = response_json.get("next_action", False)    		
    observations = f"\nThought: {thought}\nOverall task complete? {task_complete}\nCurrent step complete? {current_step_complete}\nSoftware bug? {software_bug}\nTook shortcuts? {took_shortcuts}\nNext action: {next_action}\n----------------------------------------\n\n"

    # 1. Decide on the next step (new_mode) - could remove this in favor of attending to next_action
    # Here I (Pete) decide next step based on the features of the problem
#    if took_shortcuts:
#        new_mode = "abort_shortcuts"        # or "retry" - "abort_shortcuts" might be too drastic
#    elif software_bug:
#        new_mode = "debug"
#    elif task_complete:
#        new_mode = "done"
#    elif current_step_complete:
#        new_mode = "next_step"
#    else:
#        new_mode = "continue"

    if next_action in ["debug","continue","abort_shortcuts","abort_impossible"] or isinstance(next_action, dict):	# In THESE situations, we'd like to know what the problem it saw actually was!
        print_to_user(f"Thought: {thought}")

    # Here I let the system decide directly
    # NEXT_ACTION is one of: "done", "next_step", "continue", "debug", "abort_shortcuts", "abort_impossible", "replan", {"action":"retry_earlier_step", "step_number":NUMBER, "additional_instructions":INSTRUCTIONS}    

    if next_action in ["done", "next_step", "debug", "continue", "abort_shortcuts", "abort_impossible", "replan"]:
        new_mode = next_action

    # new_mode = "retry_earlier_step" for special case of a complex next_action = {"action":..., ...}
    elif isinstance(next_action, dict):	    			# Handle complex next_action
        action = next_action.get("action", False)
        if action and action == "retry_earlier_step":
            new_step_number = next_action["step_number"]		# raise error if missing
#            additional_instructions = next_action["additional_instructions"]
            revised_instructions = next_action["revised_instructions"]
            new_mode = "retry_earlier_step"
            observation = f"I see a problem with an earlier step. Returning to step {new_step_number} to retry it with revised instructions."

            # Now we do the requested surgery on the plan
            plan = planinfo['plan']
            new_step = plan_step(plan, new_step_number)
#            updated_new_step = new_step + ". " + additional_instructions
            updated_new_step = revised_instructions
            update_plan(plan, new_step_number, updated_new_step)		# plan is destructively updated
            planinfo = {'plan':plan, 'step_number':new_step_number, 'step':updated_new_step}
            
        elif not action:
            message = f"Yikes! complex next_action is missing an 'action' field! next_action = {next_action}."
            print_to_user(message)
            raise ValueError(message)
        else:
            message = f"Yikes! Unrecognized action '{action}' in complex next_action structure! next_action = {next_action}."
            print_to_user(message)
            raise ValueError(message)
    else:
        # this has once happened, when the returned JSON didn't follow the requested schema (no 'next_action' key-value pair)
        print_to_user(f"ERROR! Unrecognized next_action '{next_action}'! Yikes!! I'll assume new_mode = 'retry'...")
#       raise ValueError("next_action should be one of: done, next_step, continue, debug, abort_shortcuts, abort_impossible, replan, {'action':...}")
        new_mode = "retry"

#    print("DEBUG: new_mode =", new_mode)
    
    # 2. Make an observation summarizing the reflection
    if new_mode in ["done", "abort_shortcuts", "abort_impossible"]:
        runtime_seconds = time.time() - my_globals.start_time if my_globals.start_time else None
        runtime = round(runtime_seconds / 60) if runtime_seconds else "?"
        if new_mode == "done":
            observation = "Step complete."
        elif new_mode == "abort_shortcuts":
            observation = "Step doesn't appear doable (a shortcut was taken). Giving up..."
        elif new_mode == "abort_impossible":
            observation = "It seems logically impossible to do this task. Giving up..."

    elif new_mode == "next_step":
        if step_number < len(plan):        
            observation = f"Step {step_number} complete. Moving onto the next step in the plan..."
            retry_counter = 0
        else:
            observation = "All the steps are finished, but the overall task isn't complete! I better replan..."
            retry_counter = 0
            new_mode = "replan"

    elif new_mode == "retry_earlier_step":
        retry_counter = 0        
        if retry_earlier_step_counter >= agent_config.MAX_EARLIER_STEP_RETRIES:
            observation = f"Too many retries from an earlier step! Giving up!"
            new_mode = "abort_iterations"
        else:
            observation = f"Step {step_number} failed, indicating a problem at an earlier step in the plan. Returning to retry that earlier step."
            retry_earlier_step_counter += 1

    elif new_mode == "continue":
        observation = f"Step {step_number} not yet complete. Let's continue to work on it..."
        retry_counter = 0

    elif new_mode == "replan":
        observation = "The current plan doesn't seem to be going anywhere. I'll replan..."
        retry_counter = 0
        
    elif new_mode in ["debug","retry"]:
        if retry_counter >= agent_config.MAX_RETRIES:
            observation = f"Too many retries! I seem to be stuck on step {step_number}. Let's abandon this effort and replan."
            new_mode = "replan"
        else:
            retry_counter += 1
            observation = f"An error occurred doing step {step_number}. Let's try and debug the problem and retry (retry number {retry_counter})."
    else:
            print_to_user(f"ERROR! Unrecognized new_mode '{new_mode}'! Yikes!!")
            raise ValueError("new_mode should be one of 'done|abort_shortcuts|next_step|continue|debug|retry'")

    print_to_user(observation)
    observations += observation + "\n"

    return new_mode, observations, planinfo

# --------------------

# plan = [{'step_number':1, 'step':"Generate"}, {'step_number':2, 'step':"Test"}]
# update_plan(plan, 2, "Answer") -> [{'step_number':1, 'step':'Generate'}, {'step_number':2, 'step':'Answer'}]
# Note this destructively updates plan
def update_plan(plan, step_number, step):
    for item in plan:
        if item.get('step_number') == step_number:
            item['step'] = step
            break  # Stop after finding and updating the first matching item
    return plan

# ======================================================================

class Tee:
    """A helper class to write to multiple streams simultaneously."""
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()  # Ensure output is written immediately        

    def flush(self):
        for stream in self.streams:
            stream.flush()

# ----------             

def print_to_user(*args, **kwargs):
    print(*args, **kwargs)

    # Capture the string
    with io.StringIO() as buffer:
        print(*args, **kwargs, file=buffer)
        output_text = buffer.getvalue()

    my_globals.print_so_far += output_text        
    
    if nora_thread_id:
        print_to_nora(output_text)

# ----------

MAX_NORA_SYSTEM_OUTPUT_LENGTH = 30 # lines in the Report Widget

def print_to_nora(output_text):
    
    global nora_system_output

    # 2. Send to the report widget in NORA
    WIDGET_SERVICE_DEV_API_URL = "https://nora-widget-service-dev.apps.allenai.org"
    BOT_USER_UUID = "6a62855f-16f1-4c09-ab76-2b9cbf815b72"
    title = "Panda"
    output_text_length = output_text.count('\n') + 1
    nora_system_output_length = nora_system_output.count('\n') + 1

    # truncate nora_system_output if necessary:
    n_to_keep = 0
    if (nora_system_output_length + output_text_length) > MAX_NORA_SYSTEM_OUTPUT_LENGTH and nora_system_output_length > n_to_keep:
        if n_to_keep == 0:
            nora_system_output = ""
        else:
            nora_system_output = "\n".join(nora_system_output.splitlines()[-n_to_keep:])           # remove all but last n_to_keep lines
        time.sleep(3) 								       # pause for effect...        

    nora_system_output += output_text    
    sections = [{"id":"123", "title":title, "tldr":nora_system_output, "text":"Working...", "citations":[]}]
    datas = json.dumps({"actor_id":BOT_USER_UUID, "thread_id":nora_thread_id, "query":title, "sections":sections})
    requests.post(f"{WIDGET_SERVICE_DEV_API_URL}/report", data=datas, timeout=30)

### ======================================================================
###  Load the advice file...
### ======================================================================

# actually, don't parse it
def read_advice_file(filepath=agent_config.ADVICE_FILE):
    try:
        with open(filepath, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print("(No advice file found)")
        return None
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")
'''
def read_advice_file(filepath=agent_config.ADVICE_FILE):
    """
    Reads a file containing "IF...THEN..." statements and returns a list of dictionaries.
    Returns: list: A list of {'if':...,'then':..} dictionaries, where each dictionary represents an "IF...THEN..." pair.
    """
    try:
        with open(filepath, 'r') as file:
            content = file.read()

        # From o3-mini:            
        # This regex looks for:
        #  1. "IF", followed by one or more whitespace characters,
        #     then lazily captures everything until "THEN".
        #  2. "THEN" (ignoring case), followed by one or more whitespaces,
        #     then lazily captures everything until the next "IF" at the start of a line or the end of the file.
        pattern = re.compile(r"IF\s+(.*?)\s+THEN\s+(.*?)(?=\nIF|\Z)", re.DOTALL)
        statements = pattern.findall(content)

        result = [{'IF': if_part.strip(), 'THEN': then_part.strip()} for if_part, then_part in statements]
        return result
    except FileNotFoundError:
        print("(No advice file found)")
        return []
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")
'''
    
# e.g., get_advice("Review existing architectures and techniques used in LLMs and agents for navigation tasks.")
def get_advice(step):
#   print("DEBUG: get_advice. ADVICE =", ADVICE)
    if ADVICE is None:
        return ""
    else:
        prompt = f"""I'm working on the following TASK: {step}
Now: Review the following list of "IF condition THEN advice" hints, and list out the applicable advice for this TASK.
In other words: For each rule where the condition matches the task, list out the advice.
Return each item of advice on a separate line, starting with a hyphen " - "
If NO advice applies, return just the empty string "". 
ONLY describe advice from the IF/THEN rules that is applicable, do NOT generate additional advice.
DO NOT return any additional text, or description of reasoning. Only return the applicable advice, if any.""" + ADVICE
        advice = call_llm(prompt, model=agent_config.PANDA_LLM)
        return advice
    


            

    
    
    
