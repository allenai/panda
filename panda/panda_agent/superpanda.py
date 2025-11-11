
# Set this flag depending if you want real or simulate experiments!
SIMULATE_EXPERIMENTS = False
#SIMULATE_EXPERIMENTS = True

"""
USAGE:
panda.run_superpanda(task="How good is OLMo at translating to French?", results_dir="tmp")		# reasonable example for SIMULATED experiments
panda.run_superpanda(report={'report_pathstem':'panda/output/language_model_temporal_reasoning_03-03-2025_18.26'}, results_dir="tmp")  # can also add {'task':...,'report_summary':...} as args in the report JSON
panda.run_superpanda(report={'report_pathstem':'panda/papers/2410.13648'}, results_dir="yuling_ToM")

Notes:
1. Provide a "results_dir" argument, used to save results: the agenda (agenda.{html,json}), agenda snapshots (N.html), and the final report (superpanda_report{.html,-raw.html}).
   The most important file to look at is:
	<results_dir>/agenda.html
   This summarizes the current state of the agenda, so you can watch progress. Reload this file to see it updated.
   Snapshots of agenda.html are stored in 1.html, 2.html, ... as the research progresses.

   Note: restarting superpanda will wipe the contents of results_dir to start fresh!

2. The actual experiments are run using run_experiment()
   There is run_experiment() code here for both REAL and SIMULATED experiments. This version runs SIMULATED experiments by default (change comments in run_experiment to change this)

# Reasonable example for REAL experiments (takes several hours)
panda.run_superpanda(task="How well can Llama do math? Use very difficult problems, and find categories where Llama struggles. Use just 10 examples.",  results_dir="math") 

# (Advanced): Does a literature search then ideates tasks automatically (again for REAL experiments)
panda.run_superpanda(topic="Can language models perform complex temporal reasoning", results_dir="temporal")	

WORKFLOW:
---------
SuperNora starts with an initial research TASK and then works through 5 steps:
 1. Experiment: Do the task using the basic Panda (run_panda()), to create a report
 2. Findings: Summarize the main findings in the report, where a finding (here) is "a discovered area of unusually poor performance"
 3. Mechanisms: Propose mechanisms that explain a finding
 4. Create Tests: to explicitly confirm/refute a mechanism
 5. Do Test: again using Panda, and decide if it confirms/refutes the mechanim

You can think of this as a branching tree of exploration, where the initial single root node is the task.

To manage the tree exploration, SuperPanda maintains an AGENDA. Each agenda_item is a different, partially explored 
branch in the tree. When an agenda_item is processed (by do_agenda_item()), it is removed from the agenda,
and one or more new agenda_items are created, representing the expansion of the leave of that branch.

EXAMPLE (slightly simplified):
------------------------------

The initial agenda has a single item, with next_step set to 'experiment' (#1 above):

  [{'task':'Test Olmo on math', 'next_step':'experiment'}]

Processing this creates a new agenda, with the path (report_pathstem) to the research report added, and next_step = 'findings' (#2 above):

  [{'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'next_step':'findings'}]

Processing this may create 3 new agenda items:

  [{'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at algebra', 'next_step':'mechanisms'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at calculus', 'next_step':'mechanisms'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at addition', 'next_step':'mechanisms'}]

Processing the first item causes ideation of possible mechanisms:

  [{'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at algebra', 'mechanism':'poor with symbols', 'next_step':'create_tests'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at algebra', 'mechanism':'abstraction hard', 'next_step':'create_tests'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at algebra', 'mechanism':'poor with variables', 'next_step':'create_tests'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at calculus', 'next_step':'mechanisms'},
   {'task':'Test Olmo on math', 'report_pathstem':'output/my_report', 'finding':'bad at addition', 'next_step':'mechanisms'}]

and so on. 

Agenda items are scored (using GPT-as-scorer) and the highest-scoring (most promising) agenda_item worked on next.

THE agenda_item DATA STRUCTURE
------------------------------
agenda_item is a (large) dict with the following keys:

 - task		   # User-specified task
 - task_json = {'topic':..., 'task':..., 'rationale':...}       # a richer description of a task produced by the ideator, if only an input topic was given
 - next_step       # initially set to "experiment"
 - dialog          # the superpanda dialog so far along this branch (only). Note the panda dialogs for specific experiments are not retained.

Processing next_step = "experiment" adds these elements:
 - report_result             # e.g., "done"
 - report_pathstem           # e.g., "panda/output/report_032"
 - report_summary            # only used for reporting purposes, no downstream usage. Can be omitted

Processing next_step = "findings" adds these elements:
 - finding = {'title':..., 'description':..., 'score':<0-10>}
 - finding_score

Processing next_step = "mechanisms" adds these elements:
 - mechanism = {'title':..., 'description':..., 'score':<0-10>}     
 - mechanism_score

Processing next_step = "create_tests" adds these elements:
 - test = {'title':..., 'description':..., 'key_measurements':..., 'expected_results_if_true':..., 'expected_results_if_false':...}

Processing next_step = "do_test" adds these elements:
 - test_report_pathstem
 - test_report_summary			  # only used for reporting purposes, no downstream usage. Can be omitted
 - confirmation = {'score':<-10 - 10>, 'explanation':...}
 - confirmation_score

After this, next_step is set to "done", indicating no more work needs to be done on this agenda_item
"""

import csv
import os
import re
import json
import datetime
import random
from string import Template		# for write_report()
from enum import Enum
from pydantic import BaseModel, Field

from panda.utils import call_llm, call_llm_json, read_file_contents, jprint, extract_html_from_string, clear_directory, copy_file, build_gpt_response_format, logger
from panda.researchworld.lit_ideation import ideate_tasks_for_topic, ideate_tasks_from_papers
from . import config as agent_config
from . import my_globals         # so run_simulated_experiment can (fake) set my_globals.print_so_far

SUPERSYSTEM_PROMPT = "You are a helpful, rigorous science assistant."

# REPORT_EXT = ".html"		# Choose whether SuperPanda "reads" the .txt or .html reports generated by Panda
REPORT_EXT = ".txt"		# Choose whether SuperPanda "reads" the .txt or .html reports generated by Panda

global agenda_dict
if 'agenda_dict' not in globals():  # Avoid overwriting it on reload
    agenda_dict = {}

# ----------

MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERPANDA_REPORT_HTML_TEMPLATE_FILE = os.path.join(MODULE_DIR, "superpanda_report_template.html")
with open(SUPERPANDA_REPORT_HTML_TEMPLATE_FILE, 'r') as f:
    SUPERPANDA_REPORT_HTML_TEMPLATE = f.read()

# ----------

# Suggested by https://chatgpt.com/c/67d0eeaf-dd38-8001-9004-b94db441f66b
TOPICS_OF_INTEREST = [
    "Theory of Mind and Social Reasoning: can LMs attribute beliefs, desires, or intentions to characters in narratives?",
    "Mathematical and Logical Reasoning: How good are models on multi-step mathematical problems, symbolic logic puzzles, and algebraic reasoning?",
    "Commonsense Reasoning: How well can models apply everyday knowledge?",
    "Chain-of-Thought and Multi-step Reasoning: How does chain-of-through reasoning impact problem-solving accuracy and transparancy?",
    "Robustness and Adversarial Testing: How is model performance affected under adversarial conditions, e.g., perturbing inputs, introducing noise?",
    "Bias, Fairness, and Ethical Reasoning: Can LMs handle socially sensitive topics? Do they perpetuate stereotypes or biases?",
    "Factual Recall and Semantic Memory: To what extent do models store and retrieve factual information?",
    "Prompt Sensitivity and Instruction Following: How much do subtle changes in input phrasing or formatting influence responses?"
    "Causal and Counterfactual Reasoning: Do models understand cause-and-effect relationships? Can they generate or evaluate counterfactual scenarios?"
    ]

# panda.panda_agent.superpanda.go()
def go():
    while True:
        topic = random.choice(TOPICS_OF_INTEREST)
        now = datetime.datetime.now()
        logger.info(f"======================================================================")
        logger.info(f"{now.hour}:{now.minute} {now.month}/{now.day}/{now.year}")
        logger.info("TOPIC:", topic)
        logger.info(f"======================================================================")
        first_word = get_first_word(topic)
        timestamp = f"{now.month}-{now.day}-{now.year}_{now.hour}.{now.minute}"
        results_dir = first_word + "-" + timestamp
        guidance = "Do this task for the language model OLMO. Start by identifying two or three types of subproblem to explore." 
        run_superpanda(topic=topic, guidance=guidance, results_dir=results_dir)

# --------------------    

# Courtesy o3-mini
def get_first_word(text):
    match = re.search(r'[A-Za-z]+', text)
    return match.group(0).lower() if match else ''

# ----------

#DEFAULT_GUIDANCE = "Do this task for the language model OLMO. Start by identifying two or three types of subproblem to explore."     # nudge panda to first carve up the problem space
DEFAULT_GUIDANCE = None

"""
Top-level entry point:
run_superpanda() should be given exactly ONE of task, tasks, topic, or a report as starting points.
"""
# panda.run_superpanda(topic="To what extent does the language model Llama have a 'theory of mind'?")
# panda.run_superpanda(topic="How well can OLMo reason about counterfactual situations or counterfactual worlds?")
# panda.run_superpanda((task="How good is Llama at 3-digit multiplication? Use 10 examples")
# panda.run_superpanda(task="Does OLMo do worse when answering questions that end in a question mark ('?') than on questions that don't have a question mark?")
# panda.run_superpanda(report={'task':..., 'report_pathstem':..., 'report_summary':...})      - see above for example of a report structure
# Example guidance: "\nAs part of the task, be sure to ideate categories of task/question/problem that were unusually difficult, where performance is surprisingly low."
def run_superpanda(task=None, task_jsons=None, topic=None, report=None, guidance=DEFAULT_GUIDANCE, results_dir=None):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to run_superpanda()!"
        logger.error(message)
        raise ValueError(message)
    
    # Check for exactly ONE input argument
    inputs = [task,task_jsons,topic,report]
    if sum(1 for input in inputs if input is not None) != 1:	
        raise ValueError("ERROR! run_superpanda must have exactly one of task, task_jsons, topic, or report as an input!")

    global agenda_dict
    agenda_dict = {}

    # Now let's build the initial list of tasks
    if task:
        task_jsons = [{'task':task}]
    if topic:
        n_tasks = 3    # let's just do the first 3 tasks
        task_jsons = ideate_tasks_for_topic(topic)[:n_tasks]	# in researchworld/lit_ideation.py

    if task_jsons:
        initial_agenda = []
        for task_json in task_jsons:
            topic = task_json.get('topic')
            task = task_json.get('task')
            rationale = task_json.get('rationale')
            task_str = (f"Topic: {topic}\n" if topic else "") + \
                       (f"Task: {task}\n" if task else "") + \
                       (f"Rationale: {rationale}\n" if rationale else "") + \
                       (f"NOTE: {guidance}\n" if guidance else "")
            task_str = task_str.strip()	# remove extra NLs
            initial_agenda_item = {'task':task_str, 'task_json':task_json, 'next_step':'experiment', 'dialog':[SUPERSYSTEM_PROMPT]}                
            initial_agenda += [initial_agenda_item]

    # Special handling for a report - might get rid of this eventually       
    else:   # no tasks -> report was given
        if not report.get('report_pathstem'):
            raise ValueError("ERROR! run_superpanda(report={...}) - report should include {'report_pathstem':...}) as a minimum requirement!")
        
        if not report.get('report_summary') or not report.get('task'):		# if task and/or report_summary missing, regenerate it
            logger.info("Summarizing report...")
            report_pathstem = report['report_pathstem']
            report_text = read_file_contents(report_pathstem + REPORT_EXT)
            if not report.get('report_summary'):
                prompt = "Generate one or two sentences that briefly summarize the conclusions of the following research paper:\n\n" + report_text
                report_summary = call_llm(prompt, model=agent_config.SUPERPANDA_LLM)
                logger.info("Report summary (inferred): %s", report_summary)
                report['report_summary'] = report_summary
            if not report.get('task'):
                prompt = "Summarize the task (research question) that this report seeks to answer in one or two sentences:\n\n" + report_text
                task = call_llm(prompt, model=agent_config.SUPERPANDA_LLM)
                logger.info("Report task (inferred): %s", task)
                report['task'] = task                

        initial_agenda_item = report				# {'task':..., 'report_pathstem':...}
        initial_agenda_item['report_result'] = 'done'
        initial_agenda_item['next_step'] = 'findings'
        initial_agenda_item['dialog'] = [SUPERSYSTEM_PROMPT]
        initial_agenda = [initial_agenda_item]

    # Clear out progress directory:
    clear_directory(results_dir)

    # Let's get going!!        
    final_agenda = do_agenda(initial_agenda, results_dir=results_dir)

    write_superpanda_report(final_agenda, results_dir=results_dir)               # or write_superpanda_report(get_agenda())   after crash/restart....

# ----------

# Restart from half-way through
# panda.panda_agent.superpanda.restart_superpanda()
def restart_superpanda(results_dir=None):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to restart_superpanda()!"
        logger.error(message)
        raise ValueError(message)

    agenda = get_agenda(results_dir=results_dir)
    final_agenda = do_agenda(agenda=agenda, save_agenda=False, results_dir=results_dir) # save_agenda=False to avoid creating a duplicate file in progress_html
    write_superpanda_report(final_agenda, results_dir=results_dir)               # or write_superpanda_report(get_agenda())   after crash/restart....    

# ----------

def get_agenda(results_dir=None):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to get_agenda()!"
        logger.error(message)
        raise ValueError(message)

    agenda_filepath = os.path.join(results_dir, "agenda.json")    
    with open(agenda_filepath, "r") as f:
        return json.load(f)

### ======================================================================
###                THE MAIN CONTROL OF THE AGENDA
### ======================================================================

def do_agenda(agenda, save_agenda=True, results_dir=None):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to do_agenda()!"
        logger.error(message)
        raise ValueError(message)

    score_agenda_items(agenda)                # updates overall_score:... for each agent_item
    agenda.sort(key=lambda item:item['overall_score'], reverse=True)  # Sorts in descending order    

    if save_agenda:
        os.makedirs(results_dir, exist_ok=True)                
        agenda_filepath = os.path.join(results_dir, "agenda.json")
        with open(agenda_filepath, "w") as f:
            json.dump(agenda, f, indent=2)    

    show_agenda(agenda, results_dir=results_dir)

    top_agenda_item = agenda[0]
    if completed_agenda_item(top_agenda_item, agenda):		# if the top-scoring agenda item is complete, nothing else can better it (scores only go down) so stop!
        logger.info("Found the optimal result!")
        return agenda
    
    next_agenda_item = get_next_agenda_item(agenda)		# first *not done* agenda item
    if next_agenda_item:
        # otherwise, let's do it!
        agenda.remove(next_agenda_item)
        new_agenda_items = do_agenda_item(next_agenda_item, results_dir=results_dir)
        new_agenda = agenda + new_agenda_items
        return do_agenda(new_agenda, results_dir=results_dir)
    else:    
        logger.info("Everything done on the agenda! (But no completed results :( )")
        return agenda

# ----------

# first non-done item. This assumes agenda is sorted
def get_next_agenda_item(agenda):
    for agenda_item in agenda:
        if agenda_item['next_step'] != 'done':
            return agenda_item
    return None

"""
----------------------------------------
	Scoring Agenda items
----------------------------------------
There are three quantitative metrics in elements of an agenda_item:
 1. finding_score: e.g., 0.2 (strength)
 2. mechanism_score: e.g., 0.5 (plausibility)
 3. mean_confirmation_score: e.g., 0.6 [ 0 (reject) to 10 (support) ]
    The mean_confirmation_score is the average confirmation score for all the (completed) tests for this particular mechanism

The OVERALL score of the agenda_item is the product of these three
"""
def score_agenda_items(agenda):
    for agenda_item in agenda:
        finding_score = agenda_item.get('finding_score', 1.0)
        mechanism_score = agenda_item.get('mechanism_score', 1.0)
        mean_confirmation_score = get_mean_confirmation_score(agenda, agenda_item) or 1.0
        overall_score = finding_score * mechanism_score * mean_confirmation_score
        agenda_item['overall_score'] = overall_score

### Take AVERAGE of confirmations (supports = 1.0, reject = 0.0)        
def get_mean_confirmation_score(agenda, agenda_item):        
    if 'confirmation_score' in agenda_item:
        confirmation_scores = []
        for agenda_item2 in agenda:
            if agenda_item2.get('mechanism') == agenda_item['mechanism'] and 'confirmation_score' in agenda_item2:
                confirmation_scores += [agenda_item2['confirmation_score']]
        mean_confirmation_score = sum(confirmation_scores) / len(confirmation_scores)
    else:
        mean_confirmation_score = None
    return mean_confirmation_score

# ----------

# agenda_item must be both "done" and all the confirmatory tests for its mechanism also done
def completed_agenda_item(agenda_item, agenda):
    if agenda_item['next_step'] != "done":
        return False
    if not agenda_item.get('mechanism'):		# e.g., initial experiment failed
        return False
    for agenda_item2 in agenda:
        if agenda_item2.get('mechanism') == agenda_item['mechanism']:
            if agenda_item2.get('confirmation_score') is None:
                return False
    return True            

### ======================================================================
###               DISPLAYING THE AGENDA
### ======================================================================

# def show_agenda(agenda, agenda_htmlpath=DEFAULT_AGENDA_HTMLPATH, save_agenda=True):
#     This rather long and complex code is at the end of this file!

# ======================================================================
#        MAIN AGENDA LINE: DOING AN ITEM IN THE AGENDA
# ======================================================================

# returns a LIST of new_agenda_items
def do_agenda_item(agenda_item, results_dir=None):

    logger.info("======================================================================")
    logger.info("NEXT AGENDA ITEM: %s", agenda_item['next_step'])
    logger.info(pretty_format_dict({k:v for k,v in agenda_item.items() if k != 'dialog'}))
    logger.info("======================================================================")
    
    dialog = agenda_item['dialog']
    next_step = agenda_item['next_step']
    
    if next_step == "experiment":						# experiment AND extract finding(s) in one go
        task = agenda_item['task']
        
        report_result, report_pathstem, report_summary = run_experiment(task, results_dir=results_dir)

        agenda_item['report_result'] = report_result
        agenda_item['report_pathstem'] = report_pathstem
        agenda_item['report_summary'] = report_summary
        if report_result != "done":
            agenda_item['next_step'] = 'done'
        else:
            agenda_item['next_step'] = 'findings'
        new_agenda_items = [agenda_item]
        return new_agenda_items

    elif next_step == "findings":
        task = agenda_item['task']
        report_pathstem = agenda_item['report_pathstem']
        report = read_file_contents(report_pathstem + REPORT_EXT)
        findings = find_failure_categories(task, report, dialog)            # EXTEND add finding_score to each
        new_agenda_items = []
        for finding in findings:
            new_agenda_item = agenda_item.copy()
            new_agenda_item.update({'finding':finding, 'finding_score':finding['score']/10, 'next_step':'mechanisms'})
            new_agenda_items += [new_agenda_item]
        return new_agenda_items

    elif next_step == "mechanisms":
        task = agenda_item['task']
        finding = agenda_item['finding']
        mechanisms = conjecture_mechanisms(task, finding, dialog)                # EXTEND to add a mechanism_score to each
        new_agenda_items = []
        for mechanism in mechanisms:
            new_agenda_item = agenda_item.copy()
            new_agenda_item.update(mechanism)
            new_agenda_item.update({'mechanism':mechanism, 'mechanism_score':mechanism['score']/10, 'next_step':'create_tests'})
            new_agenda_items += [new_agenda_item]
        return new_agenda_items

    elif next_step == "create_tests":
        mechanism = agenda_item['mechanism']
        tests = conjecture_tests(mechanism, dialog)
        new_agenda_items = []
        for test in tests:
            new_agenda_item = agenda_item.copy()
            new_agenda_item.update({'test':test, 'next_step':'do_test'})
            new_agenda_items += [new_agenda_item]
        return new_agenda_items

    elif next_step == "do_test":
        task = agenda_item['task']
        report_pathstem = agenda_item['report_pathstem']
        report = read_file_contents(report_pathstem + REPORT_EXT)
        finding = agenda_item['finding']
        mechanism = agenda_item['mechanism']
        test = agenda_item['test']          # {'title':..., 'description':..., 'key_measurements':..., 'expected_results_if_true':..., 'expected_results_if_false':...}
        result, test_report_pathstem, test_report_summary = perform_test(task, report, finding, mechanism, test, results_dir=results_dir)   # -> "done", <report-pathstem>
        logger.debug("DEBUG: result =", result)
        logger.debug("DEBUG: test_report_pathstem = ", test_report_pathstem)
        if result == "done":
            secondary_paper = read_file_contents(test_report_pathstem + REPORT_EXT)
            confirmation = assess_conjecture(task, finding, mechanism, test, secondary_paper)   # -> {"score":7,"explanation":EXP}  (score is -10 to 10)
        else:
#           test_report_pathstem = test_report_pathstem if test_report_pathstem else "n/a"
            confirmation = {"score":0, "explanation":f"(Experiment failed to complete successfully: {result})"}		        # 0 = inconclusive

        confirmation_score = (confirmation['score']+10)/20					# change -10 to 10 --> 0 to 1
        agenda_item.update({'test_report_pathstem':test_report_pathstem, 'test_report_summary':test_report_summary, 'confirmation':confirmation, 'confirmation_score':confirmation_score, 'next_step':'done'})	# finished
        new_agenda_items = [agenda_item]
        return new_agenda_items

    elif next_step == "done":
        logger.error(f"ERROR! Trying to do an agenda item that's already done!\n{agenda_item}")
        raise ValueError(f"ERROR! Trying to do an agenda item that's already done!\n{agenda_item}")

    else:
        logger.error(f"ERROR! Unrecognized next_step {next_step}!")

### ======================================================================
###               MAIN INTERFACE FOR RUNNING EXPERIMENTS
### ======================================================================

def run_experiment(task, plan=None, background_knowledge=None, reset_namespace=True, results_dir=None, allow_shortcuts=False):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to run_experiment()!"
        logger.error(message)
        raise ValueError(message)

    if SIMULATE_EXPERIMENTS:
        return run_simulated_experiment(task=task, plan=plan, background_knowledge=background_knowledge, results_dir=results_dir)
    else:
        return run_real_experiment(task=task, plan=plan, reset_namespace=reset_namespace, background_knowledge=background_knowledge, results_dir=results_dir, allow_shortcuts=allow_shortcuts)        

# --------------------

def run_simulated_experiment(task, plan=None, background_knowledge=None, results_dir=None):
    plan = "" if plan is None else "Plan: " + plan    # handle plan=None case

    background_knowledge_text = f"First consider the following background knowledge:\n" + background_knowledge if background_knowledge else ""
    prompt = f'''INSTRUCTION: Write a short, plausible, imaginary report, in plain text, summarizing research into the following task:
Task: {task}
{plan}
In the report, include a failure analysis in which you identify one or two hypothetical categories where performance was unusually poor.
Try to make the report, including its findings, as realistic as possible.
Write your report in plain text format.'''
    simulator_model = 'gpt4'
    my_globals.print_so_far = "==================== SuperPanda ====================\n" + prompt
    logger.info(my_globals.print_so_far)
    report_text = call_llm(background_knowledge_text + prompt, model=simulator_model)		# note background_knowledge_text is used, but not recorded in the history

    # fake print_so_far
    result_text = f"\n====================  {simulator_model} ====================\n" + report_text
    logger.info(result_text)
    my_globals.print_so_far += result_text
    
    timestamp = datetime.datetime.now().strftime("%m-%d-%Y_%H.%M.%S.%f")		# need to include microseconds (%f) to avoid name collisions!
    report_pathstem_superpanda = os.path.join(results_dir, "report-"+timestamp)
    report_path = report_pathstem_superpanda+REPORT_EXT
    with open(report_path, 'w') as f:
        f.write(report_text)
    result = "done"		# flag report was successful!
    report_summary = call_llm("Generate one or two sentences that briefly summarize the conclusions of this research:\n\n"+report_text)

    return result, report_pathstem_superpanda, report_summary

# ----------

def run_real_experiment(task, plan=None, background_knowledge=None, results_dir=None, reset_namespace=True, allow_shortcuts=False):
    from .panda_agent import run_panda	# delayed import, to avoid circularity
    result = run_panda(task, plan=plan, background_knowledge=background_knowledge, reset_namespace=reset_namespace, force_report=True, allow_shortcuts=allow_shortcuts)
    result_flag, report_pathstem, report_summary, token_counts = result["result_flag"], result["report_pathstem"], result["summary"], result["token_counts"]
    # Copy the Panda report (if any) into results_dir
    if report_pathstem:
        report_filestem = os.path.basename(report_pathstem)			      # "/users/pete/foo" -> "foo"
        report_pathstem_superpanda = os.path.join(results_dir, report_filestem) 	      # -> "<results_dir>/foo"
        copy_file(report_pathstem+REPORT_EXT, report_pathstem_superpanda+REPORT_EXT)   # Copy report into results_dir
    else:
        report_pathstem_superpanda = None
    return result_flag, report_pathstem_superpanda, report_summary

### ======================================================================
###                1. FIND FAILURE CATEGORIES (FINDINGS)
### This essentially just reads the values of the failure categories table
### ======================================================================

"""
Returns, for example:
findings = [{'title': 'Presence of Round Numbers', 'description': 'Questions that involved round numbers...','score':10}, ...],
            {'title': '2-digit addition', 'description': 'OLMo performs poorly on tasks involving the addition of two-digit numbers.', 'score': 10}]
"""
def find_failure_categories(task, paper, dialog):
    prompt = f"""
Read the following research report on the following task: {task}

======================================================================
        START OF REPORT
======================================================================
"""  + paper + """
======================================================================
        END OF REPORT
======================================================================

Does the report conjecture any categories of task/question/problem that were unusually difficult,
where performance was surprisingly low? Please list them using the following JSON structure:
  {"findings": [{"title":TITLE, "description":DESCRIPTION, "score":SCORE}, {...},...]}

where each finding is a category of task/question/problem that wes unusually difficult, and
SCORE is an integer rating how weak/strong the evidence is of a minor/major trend,
ranging from 0 (no evidence, no trend) and 10 (clear, conclusive evidence of a major trend).

If no such difficult categories are identified in the report, just use an empty list, e.g.,
  {"findings": []}

Go ahead!"""
    dialog.append(prompt)
    categories_json, categories_str  = call_llm_json(dialog, response_format=Findings, model=agent_config.SUPERPANDA_LLM)    
    dialog.append(categories_str)

    failure_categories = categories_json['findings']
    logger.info("failure_categories = %s", failure_categories)
    return failure_categories

# Define JSON response structure for {"findings": [{"title":TITLE, "description":DESCRIPTION, "score":SCORE}, {...},...]}
class Findings(BaseModel):
    class Finding(BaseModel):
        title:str = Field(description="Title of the problematic category")
        description:str = Field(description="Description of the problematic category")
        score:int
    findings: list[Finding]

### ======================================================================
###                2. CONJECTURE MECHANISMS
### ======================================================================

"""
Returns, for example:
mechanisms = [{'title': 'Pattern Overfitting', 'mechanism': 'OLMo may have overfitted to non-round numbers..."},
              {'title': 'Zero Processing Error', 'mechanism': "The presence of zeros in round numbers might be..."}, ...]
"""

def conjecture_mechanisms(task, failure_category, dialog):
    prompt = f"""
From the earlier research on this task: {task}
An earlier report conjectured that the following category of task/question/problem was unusually difficult:
{failure_category}

What possible mechanisms might explain such an observation? Please list some conjectures about what might cause this.
Return your answer as a JSON structure of the form:
 {{"conjectures": [{{"title":TITLE, "description":MECHANISM, "score":SCORE}}, ...]}}

where SCORE is an integer reflecting your confidence that the mechanism is real, from 0 (completely unconfident)
to 10 (very confident).
"""
    dialog.append(prompt)
    conjectures_json, conjectures_str  = call_llm_json(dialog, response_format=Conjectures, model=agent_config.SUPERPANDA_LLM)
    dialog.append(conjectures_str)
    conjectured_mechanisms = conjectures_json['conjectures']
    logger.info(f"{len(conjectured_mechanisms)} mechanisms found...")
    return conjectured_mechanisms

# Define JSON response structure for {"conjectures": [{"title":TITLE, "description":MECHANISM, "score":SCORE}, ...]}
class Conjectures(BaseModel):
    class Conjecture(BaseModel):
        title:str
        description:str
        score:int
    conjectures: list[Conjecture]

### ======================================================================
###                3. CONJECTURE TESTS
### ======================================================================

def conjecture_tests(mechanism, dialog):
    prompt = f"""
One of the conjectures that explain the initial results is:
    {mechanism}""" + """

NOW: I'd like to test this conjecture to ascertain whether it is true or not. 
Please suggest zero or more experimental tests I could do.
For each experiment, identiy what results would confirm the conjecture, or refute it.

IMPORTANT: I am only able to probe and ask questions to language models. 
I don't have access to the models' training data, and I'm not able to do experiments involving pretraining or retraining models. 
Only suggest experiments I can actually do. If the conjecture is untestable given these constraints, say so.

An experimental test of a conjecture consists of:
 - title: a title for the experiment
 - description: A description of the experiment
 - key_measurements: The key measurement(s) to make, to determine if the conjecture is true or false
 - expected_results_if_true: The results that, if obtained, would suggest the conjecture was true
 - expected_results_if_false: The results that, if obtained, would suggest the conjecture was false

Return your answer in a JSON structure of the form:
   {"tests": [{"title":<string>, "description":<string>, "key_measurements":<string>, "expected_results_if_true":<string>, "expected_results_if_false":<string>},
              {"title":<string>, "description":<string>, "key_measurements":<string>, "expected_results_if_true":<string>, "expected_results_if_false":<string>},
               ...]}

If there are no tests that are doable within my capabilities, i.e., the conjecture is untestable given my capabilities, just return an empty list of tests,
i.e., {"tests": []}
"""
    dialog.append(prompt)
    tests_json, tests_str  = call_llm_json(dialog, response_format=Tests, model=agent_config.SUPERPANDA_LLM)
    dialog.append(tests_str)

    mechanism_tests = tests_json['tests']
    logger.info("mechanism_tests = %s", mechanism_tests)
    logger.info(f"{len(mechanism_tests)} tests found...")    
    return mechanism_tests

# Define JSON response structure for {"tests": [{"title":<string>, "description":<string>, "key_measurements":<string>, "expected_results_if_true":<string>, "expected_results_if_false":<string>},..]}
class Tests(BaseModel):
    class Test(BaseModel):
        title:str
        description:str
        key_measurements:str
        expected_results_if_true:str
        expected_results_if_false:str
    tests: list[Test]
    
# ======================================================================
#               4. PERFORM A TEST
# ======================================================================

# test = {'title':..., 'description':..., 'key_measurements':..., 'expected_results_if_true':..., 'expected_results_if_false':...}
def perform_test(task, paper, finding, mechanism, test, results_dir=None):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to run_superpanda()!"
        logger.error(message)
        raise ValueError(message)
    
    background_knowledge = f"""
I'm researching the following task: {task}
My initial results are described in the below report:

======================================================================
        START OF REPORT
======================================================================
"""  + paper + f"""
======================================================================
        END OF REPORT
======================================================================

The report suggests that the following task/question/problem was unusually challenging:
{pretty_format_dict(finding)}

One possible explanation for this is the following conjecture:
{pretty_format_dict(mechanism)}

I'd now like you to test this conjecture, by performing an experiment as follows:
{pretty_format_dict(test)}
"""
    description = test['description']
    key_measurements = test['key_measurements']
    task = description + " Be sure to make the following measurements: " + key_measurements + \
        "DO NOT perform any ideation or peripheral investigations - Your SOLE task is perform an experiment to confirm or refute the conjecture being tested (about why the task/question/problem was hard)."

    result, report_pathstem, summary = run_experiment(task, background_knowledge, results_dir=results_dir)
    return result, report_pathstem, summary

### ======================================================================
###                 Simple Utility
### ======================================================================    

def pretty_format_dict(data):
    """Returns a pretty-formatted string of a dictionary with capitalized keys and values."""
    lines = []
    try: 
        for key, value in data.items():
            lines.append(f"   {key}: {value}")
        return "\n".join(lines)
    except Exception as e:
        message = f"pretty_format_dict(): Exception {e}. Input data was:\n{repr(data)}"
        logger.error(message)
        raise ValueError(message)

# ======================================================================
#               5. EVALUATE A TEST
# This is a standalone GPT query to see if the results confirm or refute a conjecture
# ======================================================================

"""
secondary_paper = utils.file_utils.read_file_contents("output/olmo_addition_performance_02-10-2025_20.03.txt")
assess_conjecture(task, failure_categories[0], conjectured_mechanisms[0], tests[0], secondary_paper)
"""
def assess_conjecture(task, failure_category, mechanism, test, paper):
    test_true = test.copy()
    del test_true['expected_results_if_false']	# just leave the expected_results_if_true, to avoid confusing the model
    prompt = f"""
An earlier project worked on the following task: {task}
The project found that the following task/question/problem was unusually challenging:
{pretty_format_dict(failure_category)}

We are now investigating why this might be the case. One possible explanation is:
{pretty_format_dict(mechanism)}                      

To test this conjecture, I performed this additional experiment:
{pretty_format_dict(test_true)}                      

That experiment is now completed, and the report is below.

Read the report, then answer the following question: Did the results support or refute the original, conjectured explanation?
Here is the report:

----------------------------------------------------------------------
                       RESEARCH REPORT
----------------------------------------------------------------------
""" + paper + """

======================================================================
        END OF REPORT
======================================================================

Now go ahead and answer the following question: Did the results support or refute the original, conjectured explanation?
In other words, did the actual results match the "expected results if true"? Or contradict/refute those expected results?
Or are the results inconclusive?
""" + """
Return your answer in a JSON structure of the form:
   {"confirmation":CONFIRMATION, "explanation":EXPLANATION}
where CONFORMATION is one of these 9 values:
"strongly_confirms", "confirms", "mildly_confirms", "hints_at_confirms", "incluclusive", "hints_at_refutes", "mildly_refutes", "refutes", "strongly_refutes"
"""
    confirmation_json, confirmation_str = call_llm_json(prompt, response_format=Confirmation, model=agent_config.SUPERPANDA_LLM)
    logger.info("confirmation_json = %s", confirmation_json)    
    confirmation = confirmation_json['confirmation']
    explanation = confirmation_json['explanation']
    conf_score = CONFIRMATION_SCORES.get(confirmation)
    if conf_score is None:
        logger.warning(f"ERROR! No confirmation value found in assess_conjecture response below. Assuming 0.\n{confirmation_str}")
        conf_score = 0
    return {"score":conf_score, "explanation":explanation}

# Define JSON response structure for {"confirmation":CONFIRMATION, "explanation":EXPLANATION}
class Confirmation(BaseModel):
    class ConfOption(str, Enum):
        C1 = "strongly_confirms"
        C2 = "confirms"
        C3 = "mildly_confirms"
        C4 = "hints_at_confirms"
        C5 = "incluclusive"
        C6 = "hints_at_refutes"
        C7 = "mildly_refutes"
        C8 = "refutes"
        C9 = "strongly_refutes"
    confirmation:ConfOption
    explanation:str

# Value equivalent    
CONFIRMATION_SCORES = {
    "strongly_confirms":10,
    "confirms":7,
    "mildly_confirms":5,
    "hints_at_confirms":3,
    "incluclusive":0,
    "hints_at_refutes":-3,
    "mildly_refutes":-5,
    "refutes":-7,
    "strongly_refutes":-10}

#Return your answer as a SCORE ranging from -10 (completely refutes the conjectured explanation), to 
#10 (completely supports the conjectured explanation), with a score of 0 meaning the report is completely inconclusive.
#
#Return your answer in a JSON structure of the form:
#   {"score":SCORE, "explanation":EXPLANATION}
#    confirmation_json,_ = call_llm_json(prompt, model=agent_config.SUPERPANDA_LLM)
#    print("confirmation_json =", confirmation_json)
#    return confirmation_json

### ======================================================================
###               DISPLAYING THE AGENDA
### ======================================================================

# panda.panda_agent.superpanda.show_agenda(panda.panda_agent.superpanda.get_agenda())
def show_agenda(agenda, results_dir=None, save_agenda=True):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to show_agenda()!"
        logger.error(message)
        raise ValueError(message)
    
    agenda_htmlpath = os.path.join(results_dir, "agenda.html")
    html_agenda = "<pre>\n"

    logger.info("Agenda:")
    for agenda_item in agenda:
        score = agenda_item['overall_score']
        task = agenda_item['task']
        
        report_result = agenda_item.get('report_result')
        report_pathstem = agenda_item.get('report_pathstem')		# might be None        
        report_summary = agenda_item.get('report_summary')		# might be None

        finding = agenda_item['finding']['title'] if 'finding' in agenda_item else None
        finding_plus = finding + ": " + agenda_item['finding']['description'] if 'finding' in agenda_item else None        

        mechanism = agenda_item['mechanism']['title'] if 'mechanism' in agenda_item else None
        mechanism_plus = mechanism + ": " + agenda_item['mechanism']['description'] if 'mechanism' in agenda_item else None        # urgh, really should call the subelement 'description' not 'mechanism'!

        test_report_pathstem = agenda_item.get('test_report_pathstem')  # might be None      
        test = agenda_item['test']['title'] if 'test' in agenda_item else None
        test_plus = test + ": " + agenda_item['test']['description'] + " <b>If true:</b> " + str(agenda_item['test']['expected_results_if_true']) if 'test' in agenda_item else None
        
        confirmation_explanation = agenda_item['confirmation']['explanation'] if 'confirmation' in agenda_item else None
        finding_score = agenda_item.get('finding_score')
        mechanism_score = agenda_item.get('mechanism_score')
        confirmation_score = agenda_item.get('confirmation_score')
        mean_confirmation_score = get_mean_confirmation_score(agenda, agenda_item)
        next_step = agenda_item['next_step']
        logger.info(f"{score:.2f}: Task: {task}; next_step: {next_step}")
        logger.info(f"      Task Result: {report_result}")                        
        logger.info(f"      Task Report Filestem: {report_pathstem}")                
        logger.info(f"      Report Summmary: {report_summary}")        
        logger.info(f"      Finding: {finding_plus}")
        logger.info(f"      Mechanism: {mechanism_plus}")
        logger.info(f"      Test: {test_plus}")
        logger.info(f"      finding_score: {finding_score:.1f}; ", end="") if finding_score else None
        logger.info(f"mechanism_score: {mechanism_score:.1f}; ", end="") if mechanism_score else None
        logger.info(f"confirmation_score: {confirmation_score:.1f}; ", end="") if confirmation_score else None
        logger.info(f"mean_confirmation_score: {mean_confirmation_score:.2f}; ", end="") if mean_confirmation_score else None
        logger.info("") if finding_score else None
        
        html_agenda += bar("", score, paren=False)
        html_agenda += "     "
        
        taskbar = bar(f" {get_id(task, 'task')} ")
        if report_pathstem:
            report_filestem = os.path.basename(report_pathstem)
            html_agenda += f'<a href="{report_filestem}{REPORT_EXT}" target="_blank">{taskbar}</a>'
        else:
            html_agenda += taskbar

        html_agenda += bar(f" {get_id(finding_plus, 'find')} ", finding_score) if finding else ""
        html_agenda += bar(f" {get_id(mechanism_plus, 'mech')} ", mechanism_score) if mechanism else ""
        
        if test:
            testbar = bar(f" {get_id(test_plus, 'test')} ")
            if test_report_pathstem:
                test_report_filestem = os.path.basename(test_report_pathstem)                
                html_agenda += f'<a href="{test_report_filestem}{REPORT_EXT}" target="_blank">{testbar}</a>'
            else:
                html_agenda += testbar                

        html_agenda += bar(f" {get_id(confirmation_explanation, 'conf')} ", confirmation_score) if confirmation_score is not None else ""
        html_agenda += bar(" mean ", mean_confirmation_score, DEFAULT_BAR_COLOR) if mean_confirmation_score is not None else ""
        html_agenda += "\n"

    logger.info("")
    html_agenda += "</pre>\n"

    for item, id in agenda_dict.items():
        html_agenda += f"<p><b>{id}:</b> {item}"		# neah, print whole thing

    if save_agenda:        
        # Write out the HTML version
        if agenda_htmlpath:
            with open(agenda_htmlpath, 'w') as f:
                f.write(html_agenda)

        # Also store a copy in a numbered file, for later animation
        os.makedirs(results_dir, exist_ok=True)            	# create directory if needed
        next_progress_path = new_progress_file(results_dir)
        with open(next_progress_path, 'w') as f:
            f.write(html_agenda)    

# --------------------

def new_progress_file(results_dir):
  file_num = 1
  while True:
    file_name = os.path.join(results_dir, f"{file_num}.html")
    if not os.path.exists(file_name):
      return file_name
    file_num += 1

# --------------------

DEFAULT_BAR_COLOR = "#6BAED6"    # calm blue
def bar(text, number=None, color=None, paren=True):
    if not color:
        if number is not None:
            color = color_for_score(number)
        else:
            color = DEFAULT_BAR_COLOR
    if number is not None:
        if paren:
            return f'<span style="background-color: {color};">{text}({number:.2f}) </span>'
        else:
            return f'<span style="background-color: {color};">{text}{number:.2f} </span>'            
    else:
        return f'<span style="background-color: {color};">{text}</span>'

# Returns an HTML color code based on a score between 0 (red) and 1 (green), courtesy Gemini
def color_for_score(score):
  if not 0 <= score <= 1:
    raise ValueError("Score must be between 0 and 1.")

  # Calculate RGB components based on linear interpolation
  red = int(255 * (1 - score))
  green = int(255 * score)
  blue = 0

  # Format as a hex color code
  return f"#{red:02X}{green:02X}{blue:02X}"

# ----------

# get_id("This is a big test", "test") -> "test001"
def get_id(string, prefix):
  if string in agenda_dict:
    return agenda_dict[string]
  else:
    existing_ids = [int(id[len(prefix):]) for id in agenda_dict.values() if id.startswith(prefix)]
    if existing_ids:
      new_id_num = max(existing_ids) + 1
    else:
      new_id_num = 0
    new_id = f"{prefix}{new_id_num:03d}"
    agenda_dict[string] = new_id
    return new_id

"""
======================================================================
		FINAL REPORT
======================================================================
Supernora identifies the best supported mechanism that might explain the main 
model weakness identified in the original seed research task. Here we
summarize that. The report itself is relatively prescribed (in 
superpanda_report_template.html) and completely derivable from the agenda.
We use GPT just to tidy it up a bit.

USAGE:
 from panda.panda_agent.superpanda import *
 write_superpanda_report(get_agenda(results_dir="ToM"))
"""
def write_superpanda_report(agenda, results_dir=None, report_filestem="superpanda_report", timestamp=True):
    if not results_dir:
        message = "ERROR! Please provide a results_dir=.. to show_agenda()!"
        logger.error(message)
        raise ValueError(message)    

    # for good measure, make sure agenda is still sorted
    score_agenda_items(agenda)               
    agenda.sort(key=lambda item:item['overall_score'], reverse=True)

    top_agenda_item = get_top_agenda_item(agenda)
    if not top_agenda_item:
        logger.info("I didn't manage to do enough research to reach a conclusion (sorry)!")
        return

    task = top_agenda_item['task']
    report_pathstem = top_agenda_item['report_pathstem']
    task_experiment_url = report_pathstem + ".html"
    top_finding = top_agenda_item['finding']
    top_finding_description = make_first_sentence_red(top_finding['description'])
    top_mechanism = top_agenda_item['mechanism']
    top_mechanism_plus = top_mechanism['title'] + ": " + top_mechanism['description']
    
    mechanisms = []
    for agenda_item in agenda:	     # collect all the mechanisms for task
        if agenda_item.get('finding') == top_finding:
            mechanism = agenda_item.get('mechanism')
            if mechanism is not None and mechanism not in mechanisms:
                mechanisms.append(mechanism)

    mechanism_plus_list = ""
    for mechanism in mechanisms:
        title = mechanism['title']
        description = mechanism['description']
        if mechanism_plus_list == "":
            mechanism_plus_list += f"<li> <b>{title}:</b> {make_first_sentence_red(description)}</span>\n"
        else:
            mechanism_plus_list += f"<li> <b>{title}:</b> {description}\n"

    test_summaries = ""
    for agenda_item in agenda:	     # collect all the tests for task
        if agenda_item.get('mechanism') == top_mechanism:
            test = agenda_item.get('test')
            if test is not None and agenda_item.get('confirmation'):    # test must actually have been done
                title = test['title']
                description = make_first_sentence_red(test['description'])
                if_true = test['expected_results_if_true']
                test_report_pathstem = agenda_item['test_report_pathstem']
                confirmation = agenda_item['confirmation']
                outcome = make_first_sentence_red(confirmation['explanation'])
                degree_of_support = agenda_item['confirmation_score']
                test_summary = f"""
<b>Test:</b> {title}<br>
<b>Description:</b> {description}<br>
<b>If True:</b> {if_true}<br>
<b>Outcome:</b> {outcome}<br>
<b>Estimated degree of support:</b> {degree_of_support:.2f}<br>
<b>Report:</b> <a href="{test_report_pathstem}.html" target='_blank'>here</a>
<p>
"""
                test_summaries += test_summary

    # As a nicity, add a pretty conclusion
    prompt = f"""Please write a couple of sentences of conclusion for the following research I did. The research was as follows:
For the task: {task}
I found tnat models sometimes struggle with: {top_finding_description}
From further investigation, this appears to be because: {top_mechanism_plus}"""
    conclusion = call_llm(prompt, model=agent_config.SUPERPANDA_LLM)

    html_report_template = Template(SUPERPANDA_REPORT_HTML_TEMPLATE)
    html_report_parameters = {
        'task':task,
        'task_experiment_url':task_experiment_url,
        'top_finding_description':top_finding_description,
        'mechanism_plus_list':mechanism_plus_list,
        'top_mechanism_plus':top_mechanism_plus,
        'test_summaries':test_summaries,
        'conclusion':conclusion}
    html_report = html_report_template.substitute(html_report_parameters)

#    prompt = """Tidy up the below report, to make it a bit more fluent and fill in the items marked with square brackets [].
#Try not to lengthen it. Your new report should also be in HTML\n\n"""
#    logger.info(f"Tidying up the report using {agent_config.SUPERPANDA_REPORT_WRITER_LLM}...")
#    improved_html_report_str = call_llm(prompt+html_report, model=agent_config.SUPERPANDA_REPORT_WRITER_LLM)
#    improved_html_report = extract_html_from_string(improved_html_report_str)

    date_for_filestem = datetime.datetime.now().strftime("%m-%d-%Y_%H.%M")        
    tweaked_filestem = report_filestem + "_" + date_for_filestem if timestamp else report_filestem
    report_pathstem = os.path.join(results_dir, tweaked_filestem)
    html_report_file = report_pathstem + ".html"
#    html_improved_report_file = report_pathstem + ".html"    

    with open(html_report_file, "w") as file:
        file.write(html_report)

#    with open(html_improved_report_file, "w") as file:
#        file.write(improved_html_report)

    logger.info("Reports written to:")
    logger.info(" - %s", html_report_file)
#   logger.info(" - %s", html_improved_report_file)

#   return html_improved_report_file
    return html_report_file

### ----------        

# first done item. This assumes agenda is sorted
def get_top_agenda_item(agenda):
    for agenda_item in agenda:
        if agenda_item['next_step'] == 'done' and agenda_item.get('confirmation'):	# check we completed the tasks, and didn't abort
            return agenda_item
    return None

# ----------

def make_first_sentence_red(text):
  sentences = text.split('.')
  first_sentence = sentences[0].strip()

  if not first_sentence:
      return text #if the first sentence is empty, return the original text.

  if len(sentences) == 1:
      return f'<span style="color: red;">{first_sentence}</span>'

  remaining_text = '.'.join(sentences[1:]).strip()
  if remaining_text:
    return f'<span style="color: red;">{first_sentence}.</span> {remaining_text}'
  else:
    return f'<span style="color: red;">{first_sentence}.</span>'

    
    
   
 
