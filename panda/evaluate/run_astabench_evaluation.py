
"""
panda.evaluate.run_astabench_evaluation.run_astabench()

NOTE: If the results file already exists, this function will skip that eval (won't redo it)

TARGETS = ["idea-98-simplified","idea-100-simplified","idea-127-simplified","idea-134-simplified","idea-141-simplified","idea-173-simplified","idea-177-simplified","idea-189-simplified","idea-301-simplified","idea-304-simplified","idea-361-simplified"]

# NEW:
panda.run_astabench_tasks(task_file="panda/evaluate/astabench_tasks_may_2025.json", results_dir="panda/astabench_may_2025-claude40/", allow_shortcuts=True)

panda.run_astabench_tasks(task_file="panda/evaluate/astabench_tasks_may_2025.json", results_dir="panda/astabench_may_2025_extra/", allow_shortcuts=True, model="gpt-4.1", targets=)

panda.run_astabench_tasks(task_file="panda/evaluate/astabench_hyper_tasks.json", solver="faker", results_dir="hyper_results", allow_shortcuts=True)

Simplest usage:
panda.run_astabench_tasks()
panda.run_astabench_tasks(task_file="panda/evaluate/panda_hyper_tasks.json", results_dir="panda/hyper_results/")
panda.run_astabench_tasks(task_file="panda/evaluate/astabench_tasks_may_2025.json", results_dir="panda/astabench_may_2025/", allow_shortcuts=True, model="gpt-4.1")

# --------------------
# New Hyper tasks:
panda.run_astabench_tasks(task_file="panda/evaluate/harpa_AutoNora_format.json", results_dir="harpa_AutoNora_format/", allow_shortcuts=True, model="gpt-4.1")
panda.run_astabench_tasks(task_file="panda/evaluate/harpa_AutoNora_format.json", results_dir="harpa_AutoNora_format/", allow_shortcuts=True, model="gpt-4.1", targets=TARGETS)
TARGETS = ["idea_12","idea_20","idea_21","idea_24","idea_26","idea_42","idea_44"]
panda.run_astabench_tasks(task_file="panda/evaluate/harpa_AutoNora_format.json", results_dir="harpa_AutoNora_format/", allow_shortcuts=True, model="gpt-4.1", targets=['idea_21'])

# will try harder, including allowing shortcuts when necesssary rather than giving up:
panda.run_astabench_tasks(task_file="panda/evaluate/panda_hyper_tasks.json", results_dir="panda/hyper_results/", allow_shortcuts=True)

panda.run_astabench_tasks(task_file="panda/evaluate/panda_astabench_tasks.json", \
			     results_dir="panda/astabench",  \
			     solver="Panda", 		# Just two options: solver = "Panda" (default) or "faker" \
                             model="o3-mini",
                             allow_shortcuts=True)		# Keep going, even if Panda took a shortcut 

NOTE: We insist that each task in task_file has a substring TASK_DIVIDER = "------ end of task definition -----" separating the task from the response format specification.
"""

import os, glob
import pandas as pd
import traceback
import json
import shutil

from panda.utils import read_file_contents, file_exists, call_llm, call_llm_json
from panda.panda_agent import run_panda, save_dialog, get_dataframes
from panda.panda_agent import config as agent_config

from panda.utils import config as utils_config

from panda.panda_agent import my_globals         # leave "my_globals." prefix on globals for now, for clarity
from panda.panda_agent import panda_agent_subprompts
import panda.researchworld.tools as tools
import panda.researchworld.ideate_categories as ideate_categories

# panda.evaluate.run_astabench_evaluation.run_astabench()
def run_astabench():
    print("NOTE: Doing easy dev...")
    run_astabench_tasks(task_file="c://users/peter/Dropbox/Desktop/2025/Panda/astabench_e2e_discovery/dev_may_2025.json", results_dir="panda_easy_dev_results_gpt5", allow_shortcuts=True)
    print("NOTE: Doing hard dev...")    
    run_astabench_tasks(task_file="c://users/peter/Dropbox/Desktop/2025/Panda/astabench_e2e_discovery/dev_jun_2025_harpa.json", results_dir="panda_hard_dev_results_gpt5", allow_shortcuts=True)
    print("NOTE: Doing easy test...")
    run_astabench_tasks(task_file="c://users/peter/Dropbox/Desktop/2025/Panda/astabench_e2e_discovery/test_may_2025.json", results_dir="panda_easy_test_results_gpt5", allow_shortcuts=True)
    print("NOTE: Doing hard test...")    
    run_astabench_tasks(task_file="c://users/peter/Dropbox/Desktop/2025/Panda/astabench_e2e_discovery/test_jun_2025_harpa.json", results_dir="panda_hard_test_results_gpt5", allow_shortcuts=True)

### ======================================================================
###	1. RUN ASTABENCH TASKS
### ======================================================================

ASTABENCH_RESULTS_DIR = "astabench"		# top-level
#ASTABENCH_TASKS_FILE = "panda/evaluate/astabench_tasks_may_2025.json"
ASTABENCH_TASKS_FILE = "panda/evaluate/harpa_AutoNora_format.json"

def run_astabench_tasks(task_file=ASTABENCH_TASKS_FILE, results_dir=ASTABENCH_RESULTS_DIR, solver="Panda", model=agent_config.PANDA_LLM, allow_shortcuts=False, targets=None):

    os.chdir(agent_config.ROOT_DIR)		# make sure you're back at the top    

    os.makedirs(ASTABENCH_RESULTS_DIR, exist_ok=True)    	# check dir exists
    with open(task_file, "r", encoding='utf-8', errors="ignore") as f: 
        tasks = json.load(f)

    for task in tasks:
        tid = task["id"]
        task_and_json = task["problem_description"]
        if targets and tid not in targets:		# if targets provided, only do those targets
            continue					# i.e., skip
        if solver == "Panda":
            run_astabench_task(tid, task_and_json, results_dir=results_dir, allow_shortcuts=allow_shortcuts, model=model)
        elif solver == "faker":
            run_astabench_task_faker(tid, task_and_json, results_dir=results_dir, model=model)
        else:
            print("ERROR! Unrecognized solver", solver, "!")
    print("ASTABench Evaluation done!")

### ======================================================================
###	3. RUN **FAKE** ASTABENCH TASK
### ======================================================================

def run_astabench_task_faker(tid:int, task_and_json:str, results_dir=ASTABENCH_RESULTS_DIR, model=agent_config.PANDA_LLM):

    target_report_filestem = str(tid)
    target_results_filestem = f"{target_report_filestem}-results"
    results_json_path = os.path.join(results_dir, target_results_filestem + ".json")
    results_readable_path = os.path.join(results_dir, target_results_filestem + "_readable.txt")

    if file_exists(results_json_path):
        print("(Task", tid, "already run)")
        return

    try:
        prompt = task_and_json + """
As you don't have the ability to actually do this research, please make up the report, code, trace/log, and artifacts as best you can, to simulate a successful piece of research.
"""
        print("Doing task", tid, "...", end="")
        results, results_str = call_llm_json(prompt, model=model)		# HERE'S THE MAIN CALL
        print("done!")

        # Save normal JSON
        with open(results_json_path, "w", encoding="utf-8") as file:
            json.dump(results, file, indent=2)

            # Save newline-expanded version (not valid JSON anymore)
        with open(results_readable_path, "w", encoding="utf-8") as file:
            raw_json = json.dumps(results, indent=2)
            readable = raw_json.replace("\\n", "\n")  # unescape "\n" to real newlines
            file.write(readable)

    except Exception as e:
        print("Fake solver failed: Exception", e)

### ======================================================================
###	2. RUN ASTABENCH TASK
### ======================================================================

TASK_DIVIDER = "------ end of task definition -----"

# Return value: Irrelevant
# run_astabench_task("idea-387-simplified", "", results_dir="panda/tmp")
def run_astabench_task(tid:int, task_and_json:str, results_dir=ASTABENCH_RESULTS_DIR, allow_shortcuts=False, model=agent_config.PANDA_LLM):

    print("DEBUG: Running ASTABench task", tid, "...")
    os.makedirs(results_dir, exist_ok=True)

    if TASK_DIVIDER not in task_and_json:
        print(f"ERROR! The phrase '{TASK_DIVIDER}' was missing in task ID {tid}. Please correct this item in the task_file!")
        return
        
    task = task_and_json.split(TASK_DIVIDER)[0]
    target_report_filestem = str(tid)
    target_report_pathstem = os.path.join(results_dir, target_report_filestem)    
#    target_trace_filestem = f"{target_report_filestem}-trace"
    target_code_filestem = f"{target_report_filestem}-code"
    target_results_filestem = f"{target_report_filestem}-results"
    target_done_filestem = f"{target_report_filestem}-done"
    target_dataset_filestem = f"{target_report_filestem}-dataset"
    report_text = None

#    results_json_path = os.path.join(results_dir, target_results_filestem + ".json")    
#    if file_exists(results_json_path):
#        print("(Task", tid, "already run)")
#        return
    
    target_done_path = os.path.join(results_dir, target_done_filestem + ".txt")
    if file_exists(target_done_path):
        with open(target_done_path, 'r', encoding='utf-8') as f:
            done_flag = f.readline().strip()
        if done_flag == "done":
            print("(Task", tid, "already run)")
            return
        else:
            print("Task", tid, "NOT successful (status:", done_flag, ") - deleting attempt and retrying...")

    print("Deleting any old files from partial prior runs...")            
    for filepath in glob.glob(target_report_pathstem + '-*'):	# e.g., idea3-trace.txt
        if os.path.isfile(filepath):  # Ensure it's a file, not a directory
            os.remove(filepath)
            print(f"Deleted: {filepath}")
    for filepath in glob.glob(target_report_pathstem + '.*'):	# e.g., idea3.{txt,py,...}
        if os.path.isfile(filepath):  # Ensure it's a file, not a directory
            os.remove(filepath)
            print(f"Deleted: {filepath}")
    
    try:
        
        # ========================================
        # Note: allow_shortcuts=True means Panda *doesn't* check for faking bits it can't manage, and instead allows it to always try its hardest...
        result = run_panda(task=task, force_report=True, allow_shortcuts=allow_shortcuts, model=model)	# where the action happens!!!!
        result_flag, report_pathstem, summary, token_counts = result["result_flag"], result["report_pathstem"], result["summary"], result["token_counts"]

        # ========================================
        
        print(f"Evaluation complete for task {tid}!")
        print(f"Panda task: {task}")        
        print(f"Panda result: {result_flag}")
        print(f"Panda report file: {target_report_pathstem}.txt")

        # [1] Write out the "done" flag
        with open(os.path.join(results_dir, target_done_filestem + ".txt"), "w", encoding="utf-8") as file:
            file.write(result_flag+"\n")

        # [2] Write out (copy) the report files (txt, html)            
        if result_flag == "done":
            shutil.copy(report_pathstem + ".txt", target_report_pathstem + ".txt")	# panda makes up its own name for a report, so need to change it
            shutil.copy(report_pathstem + ".html", target_report_pathstem + ".html")

            # GET THE REPORT TEXT
            report_text = read_file_contents(target_report_pathstem + ".txt")

        # [3] (Re)output the dialog (-trace, -trace-long)           
        save_dialog(output_dir=results_dir, output_filestem=target_report_filestem)				# record dialog, even if failure

        report_trace = my_globals.print_so_far					
#       trace_summary = report_trace
        trace_summary = summarize_trace(report_trace)							# trace summary

        # [4] (Re)output the code
        code = my_globals.code_so_far	# already saved now, in save_dialog
        codefile = os.path.join(results_dir, target_report_filestem + ".py")

        # [5] Output the artifacts (again - some already output 
        dataset_n = 0
        artifacts = []        
        named_dataframes = get_dataframes(my_globals.code_so_far)
        for dataframe_name, dataframe in named_dataframes:
            dataset_filename = os.path.join(results_dir, target_report_filestem + "-df-" + dataframe_name + ".json")            # recoreded 
            dataset_contents = get_dataframe_head_size_limited(dataframe)
            artifacts += [{"filename":dataset_filename, "artifact":dataset_contents}]        

        # [6] Assemble the actual results structure that the AstaBench evaluator cares about
        results = {"results":{
            "report": report_text or summary,
            "code": [{"filename": codefile, "code": code}],
            "trace": trace_summary,            
            "artifacts": artifacts,
            "token_counts": token_counts}}

    except Exception as e:
        tb = traceback.format_exc()         
        results = f"Task failed (Error below)\nPanda Python error: {e}!\nTraceback:\n{tb}"
        print(results)
        # [1] Re-write out the "done" flag
        with open(os.path.join(results_dir, target_done_filestem + ".txt"), "w", encoding="utf-8") as file:
            file.write("abort_python_error\n")

    # [7] Write out the results structure        
    results_json_path = os.path.join(results_dir, target_results_filestem + ".json")			# defined earlier
    results_readable_path = os.path.join(results_dir, target_results_filestem + "_readable.txt")

    # Save normal JSON
    with open(results_json_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    # Save newline-expanded version (not valid JSON anymore)
    with open(results_readable_path, "w", encoding="utf-8") as file:
        raw_json = json.dumps(results, indent=2)
        readable = raw_json.replace("\\n", "\n")  # unescape "\n" to real newlines
        file.write(readable)

    return results

# ----------

MAX_JSON_LENGTH = 10000  # Max allowed JSON string length per artifact

# get the first 50 rows (or less) of the dataframe, making sure the max returned lengh is 10k
def get_dataframe_head_size_limited(dataframe, max_rows=50, max_chars=MAX_JSON_LENGTH):
    """
    Return a JSON string of up to `max_rows` from the dataframe, but no more than `max_chars` characters.
    Always includes at least 1 row.
    """
    for n in range(max_rows, 0, -1):
        head = dataframe.head(n)
        json_str = head.to_json(orient="records", lines=True)
        if len(json_str) <= max_chars or n == 1:
            return json_str
    return ""  # Should never reach here due to the n == 1 condition

# ----------
    
"""
TARGET RESULT FORMAT FOR ASTABENCH
{
    "results": {
        "report"(str): <report>,
        "code"(list): [
            {"filename"(str): <filename1>, "code"(str): <code1>},
            {"filename"(str): <filename2>, "code"(str): <code2>},
            ...
        ],
        "trace"(str): <trace>,
        "artifacts"(list): [
            {"filename"(str): <filename1>, "artifact"(str): <artifact1>},
            {"filename"(str): <filename2>, "artifact"(str): <artifact2>},
            ...
        ]
    }
}
"""    

# ======================================================================
                          
def summarize_trace(report_trace):
    prompt = """
Below is a trace of an autonomous agent performing a research task. I'm wanting a shortened summary of this trace, detailed enough to check that the agent did the right thing, but shorter than the full trace. Please create such a shorted summary. Take care to include important code snippets so that a reader can check the code implementation matches the intended steps.

======================================================================
======================================================================
	START OF TRACE
======================================================================
======================================================================
""" + report_trace + """
======================================================================
======================================================================
	END OF TRACE
======================================================================
======================================================================
"""
    summary = call_llm(prompt)
    return summary

# ======================================================================
#		FIND SUCCESSFUL RUNS (Utility, NOT USED)
# ======================================================================

# panda.evaluate.run_astabench_evaluation.move_done_runs(results_dir="panda/astabench_may_2025", target_dir="panda/astabench_may_2025_failed", move_if="abort_beyond_capabilities")
def move_done_runs(results_dir=ASTABENCH_RESULTS_DIR, target_dir=None, move_if="done"):
    filestems = find_done_runs(results_dir=results_dir, move_if=move_if)
    for filestem in filestems:
        for filename in os.listdir(results_dir):
            if filename.startswith(filestem):
                src_path = os.path.join(results_dir, filename)
                dst_path = os.path.join(target_dir, filename)
                shutil.move(src_path, dst_path)

# panda.evaluate.run_astabench_evaluation.find_done_runs()
def find_done_runs(results_dir=ASTABENCH_RESULTS_DIR, move_if="done"):
    matching_files = []
    for filename in os.listdir(results_dir):
        if filename.endswith("-done.txt"):
            file_path = os.path.join(results_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                if move_if in f.read():
                    matching_files.append(filename.removesuffix("-done.txt"))
    print(matching_files)
    return matching_files

"""
# Temporary
def fix_encoding(obj, src_encoding="latin-1"):
    if isinstance(obj, dict):
        return {fix_encoding(k, src_encoding): fix_encoding(v, src_encoding) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [fix_encoding(i, src_encoding) for i in obj]
    elif isinstance(obj, str):
        try:
            return obj.encode(src_encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return obj  # Return as-is if fix fails
    else:
        return obj
"""
