
"""
Simplest usage:
run_evaluation()
run_evaluation(dataset_path='tmp2.csv', results_file='test_results.csv', eval_dir='test')
"""

import csv
import os
import traceback

from panda.utils import clear_directory, read_file_contents
from panda.utils import call_llm_json     			# for scoring using LLM-as-judge

from panda.panda_agent import run_panda, save_dialog

from . import config
from .score_answer import score_answer

# ======================================================================
#		EVALUATOR
# ======================================================================

"""
def run_evaluation(dataset_path="norabench_tasks.csv", results_file="norabench_results.csv", eval_dir=config.DEFAULT_EVAL_DIR, restart=True):
Purpose:
    Run a batch evaluation of Panda on a set of predefined tasks
Args:
    dataset_path (str): The full path (including directory, if needed to the dataset = a CSV file with columns:
	'tid' (task ID, an integer), e.g., 1
	'topic' (the topic of the task), e.g., "theory of mind"
	'task' (the actual task), e.g., "How well do LLMs track nested incorrect beliefs?"
	'rationale' (a paragraph-length description of the task)
    results_file (str): File name (no path) for the CSV results
    eval_dir (str): The results_file and Panda reports will all be placed in this directory
    restart (Boolean): By default, the evaluator restarts. But if False, it will only run tests NOT already reported
         in results_file. This allows us to restart after errors without restarting from scratch.
Returns:
    (nothing)
Side-Effects:
    results_file: For each task not already scored in results_file, Panda is run, a report is 
        generated and scored, and results_file is updated to add those scores in.
    eval_dir: The new reports and execution traces are added to aval_dir.
Example:
    run_evaluation(dataset_path="panda/evaluate/norabench_tiny_tasks.csv", results_file="norabench_tiny_results.csv", target_tids=[1])
"""
def run_evaluation(dataset_path="panda/evaluate/norabench_tiny_tasks.csv", results_file="norabench_tiny_results.csv", eval_dir=config.DEFAULT_EVAL_DIR, restart=True, target_tids=None):

    # flush out eval_dir (unless restart = False)
    if not os.path.exists(eval_dir):
        os.makedirs(eval_dir)
    elif restart:
        if input(f"Restarting the evaluation: I'm about to flush all files in the evaluation directory '{eval_dir}/'...ok? (<return> to continue, 'n' to abort)? ") == 'n':
            print("Halting evaluation!")
            return
        else:
            clear_directory(eval_dir)
        
    results_path = os.path.join(eval_dir, results_file)

    # 1. read in the NORABench dataset
    try:
        with open(dataset_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile) 
            dataset = list(reader)
    except FileNotFoundError:
        print(f"Dataset file {dataset_path} not found! (doesn't exist)?")
        raise
    except Exception as e:
        raise RuntimeError(f"Error processing file '{dataset_path}': {e}")

    # 2. Create/clean out the results file (unless restart = False)
    if restart or not os.path.exists(results_path):
        with open(results_path, 'w', newline='', encoding='utf-8') as csvfile: 
            pass
        
    # 3. Read in results file contents to see which tasks still need to be done
    with open(results_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile) 
        results_data = list(reader)
        already_done_tids = [row['tid'] for row in results_data if 'tid' in row]

    # 4. Now! Actually do the evaluation for tasks not already done (in the results _file)            
    for row in dataset:
        tid = row['tid']
        task = row['task']

        if tid not in already_done_tids and (not target_tids or (tid in target_tids)):

            print(f"""======================================================================
EVALUATING ON TASK {tid}
======================================================================""")

            ## THE MAIN EVALUATION LOOP!!
            ## 1. Run Panda
            result, report_text, report_pathstem = run_task(tid, task, eval_dir=eval_dir)
        
            ## 2. Score the result
            score, scores_json = score_answer(task, report_text)
        
            # Write the scores to a file
            results_data = {'tid':tid, 'task':task, 'result':result, 'report_pathstem':report_pathstem} | scores_json | {'average score':score}
            with open(results_path, 'a', newline='', encoding='utf-8') as csvfile:	# [1]
                writer = csv.DictWriter(csvfile, fieldnames=results_data.keys())
                if csvfile.tell() == 0:  		# Check if file is empty (no header row)
                    writer.writeheader() 
                writer.writerow(results_data)

### ======================================================================
###	1. RUN TASK
### ======================================================================

"""
def run_task(tid:int, task:str, eval_dir:str=config.DEFAULT_EVAL_DIR):
Purpose:
    Run Panda on a task. If successful, run_task returns a report and also places it in eval_dir.
Args:
    tid (int): The Task ID
    task (str): The task itself (typically a sentence)
    eval_dir (str): Where to place the reports (of successful tasks)
Returns:
    result (str): "done" if the task is completed, otherwise various strings indicating failure mode
    report (str): If result == "done", the TXT version of the report (also placed in eval_dir).
                  Otherwise returns None.
    report_pathstem (str): The path to the report file itself
"""
def run_task(tid:int, task:str, eval_dir:str=config.DEFAULT_EVAL_DIR):
    target_report_filestem = str(tid)
    target_report_pathstem = os.path.join(eval_dir, target_report_filestem)    
    target_trace_filestem = f"{target_report_filestem}-trace"
    report_text = None
    try:
        result, report_pathstem, summary, token_counts = run_panda(task=task, force_report=True)
        print(f"Evaluation complete for task {tid}!")
        print(f"Panda task: {task}")        
        print(f"Panda result: {result}")
        print(f"Panda report file: {target_report_pathstem}.txt")
        if result == "done":
            os.rename(report_pathstem + ".txt", target_report_pathstem + ".txt")	# panda makes up its own name for a report, so need to change it
            os.rename(report_pathstem + ".html", target_report_pathstem + ".html")            
            report_text = read_file_contents(target_report_pathstem + ".txt")
        save_dialog(output_dir=eval_dir, output_filestem=target_trace_filestem)	# record dialog, even if failure        
    except Exception as e:
        tb = traceback.format_exc()
        result = f"Panda Python error: {e}!"
        print(f"Evaluation FAILED for task {tid}.")
        print(result)
    return result, report_text, target_report_pathstem

