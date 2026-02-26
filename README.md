# Panda v1.5.1

# Overview

Panda is an autonomous research agent that implements an outer-loop of plan-do, and an inner-loop that iterates act-reflect over each step of the plan. The agent controller architecture itself is completely general, but is customized for research by virtue of a large prompt and set of research-oriented Python functions documented in that prompt.

For an example output report and trace, see the /output directory. The .html files are (rather naive) final reports, and the \-trace.txt files show the execution trace of panda running on a few illustrative tasks.

# Usage

## Instructions

1. Panda makes calls to an underlying LLM, the default is set in PANDA_LLM in panda_agent/config.py. (You can also specify a different one at runtime). 

2. Make sure you have the appropriate API keys set for the LLM(s) you need (e.g., for PANDA_LLM defined in panda_agent/config.py, currently Claude).  If you want to use OpenAI (GPT), set in the environment variable OPENAI\_API\_KEY. If you want to use Mistral/LLama, set TOGETHER\_API\_KEY. If you want to use Claude, set ANTHROPIC\_API\_KEY.

3. **Either** Run from Python. Create a new conda environment for panda:

```
% git clone https://github.com/allenai/panda.git
% cd panda
% conda create -n panda
% conda activate panda
(panda) % conda install pip                  # if not installed
(panda) % pip install -e .
% conda activate panda                       # if not already in panda environment
(panda) % python run_panda.py "What is 1 + 1?" [--force_report] [--outputs_dir <directory>]
```
With optional arguments:
  --force_report     - force Panda to *always* write a report on its work
  --outputs_dir      - directory for the experimental results directory (containing report and other artifacts). Default is current working directory.

3.2 **OR** Run as a tool:

```
# Install globally using uv
uv tool install git+https://github.com/allenai/panda
```
Then in the tool call:

1. describe the research task (TASK) and (optionally) background knowledge (BACKGROUND_KNOWLEDGE), **or**
2. provide paths to *files* that contain
     a. the task (TASK_FILE)
     b. (optionally) the background knowledge (BACKGROUND_KNOWLEDGE_FILE)

also you can optionally provide:
  3. a directory to place the experimental outputs in (OUTPUTS_DIR). This defaults to the current working directory.
  4. a path to a JSON file to place the result summary in (RESULT_FILE). If not specified, the result is only returned from this tool call to the user and not saved to disk.

This looks like, for supplying the task in-line:
```bash
panda --task TASK --background_knowledge BACKGROUND_KNOWLEGE --force_report --result_file RESULT_FILE --outputs_dir OUTPUTS_DIR
```
For example:
```bash
panda --task "Perform an experiment to assess how good gpt-4o is at translating into French. Use just 5 test examples." --force_report --outputs_dir "C:/Users/peter/my_project/experiments/" --result_file "C:/Users/peter/my_project/result.json"
```
or for supplying the task using files:
```bash
panda --task_file TASK_FILE --background_knowledge_file BACKGROUND_KNOWLEGE_FILE --force_report --result_file RESULT_FILE --outputs_dir OUTPUTS_DIR
```
for example:
```
```bash
panda --task_file "C:/Users/peter/my_project/task.txt" --background_knowledge_file "C:/Users/peter/my_project/background_knowledge.txt" --force_report --outputs_dir "C:/Users/peter/my_project/experiments/" --result_file "C:/Users/peter/my_project/result.json"
```

3.3 **OR** Run from iPython interactively
To run, go the top-level panda directory, then start ipython:
```
% conda activate panda                       # if not already in panda environment
(panda) % ls
README.md     panda/     setup.py      LICENCE      VERSION     (etc)
(panda) % ipython
In [1]: import panda
In [2]: panda.run_panda()
What is the next research action/task you'd like me to do (or 'q' to quit)? End with blank line (**HIT RETURN TWICE**) 
> How good is Llama at math?
```

**NOTE** hit \<return\> ***twice*** after you enter your task. If nothing seems to be happening, it's likely because you need to hit \<return\> a second time.

You can alternatively pass the task as an argument

```
In [4]: result = panda.run_panda(task="What is 1 + 1?", force_report=True)
In [5]: print(result)
{'result_flag': 'done',
 'report_pathstem': 'c:/Users/peter/Dropbox/Desktop/2025/Panda/panda/subdir_of_panda/experiment-20251111-095236/experiment',
 'summary': 'The research successfully determined that 1 + 1 equals 2 through direct arithmetic calculation.',
 'token_counts': [{'model': 'claude-sonnet-4-20250514','prompt_tokens':54843,'completion_tokens':341,'total_tokens':55184}]}
```
Notes:
 * A result of "done" indicates the research was successful, anything else and it failed.
 * "force_report=True" *forces* Panda to produce a report (even if the research was unsuccessful).
 * The report_filestem shows where the .html and .txt reports are, as well as the -trace.txt and -trace-long.txt log files.
 * The summary is a short GPT-generated summary for the user.

The full list of arguments are given in panda/panda_agent/panda_agent.py (defaults shown below):
```
run_panda(task=None, background_knowledge=None, force_report=False, allow_shortcuts=False, model=agent_config.PANDA_LLM, outputs_dir="output")
```
* **task** (txt): The task to perform, e.g., "How good is Llama at math?"
* **background_knowledge** (txt): Any background knowledge to include in the context when planning
* **force_report=True** (default False): Make Panda **always** produce a report (if the experiment succeeds), even if the research plan doesn't explicitly call for one.
* **allow_shortcuts=True** (default False): Allow Panda to keep going if it takes a shortcut (allows partial credit during evaluations), otherwise it will give up (abort).
* **model**: The underlying LLM to use. Default is set in PANDA_LLM in panda_agent/config.py.
* **outputs_dir**: By default, the resulting experiment-<date>-<time>/ directory is created as a subdirectory of outputs_dir. outputs_dir is relative to the Panda dir itself.

3.4 Via MCP, linked to Cursor
Edit panda/mcp.json appropriately to point to the Python containing the Panda library files, then place in the ~/.cursor/ folder. Connection is .cursor/mcp.json -> python[that contains panda environment] panda.mcp_server (which imports panda) -> panda.run_panda()

## Examples

Some example tasks you can try, e.g.,
```
(panda) % python run_panda.py "What is 1 + 1?" 
```
or in iPython:
```
In [4]: panda.run_panda(task="What is 1 + 1?", force_report=True)
```
* What is 1 + 1?
* Does Llama know what 245 \* 2414 is?
* Does Llama do worse when answering questions that end in a question mark ('?') than on questions that don't have a question mark?
* Which language model is better at telling jokes, Claude, Llama, or Mistral?  
* How much do Claude and LLama find the same types of questions difficult in math?  
* Is Llama capable of behaving deceptively?  
* Is Llama capable of generating hate speech?  
* Which foreign languages does Llama know best?

# Description

This codebase implements a version of Panda, a simple, autonomous "discovery" system which plans and performs software experiments. The agent controller (panda/panda\_agent/panda\_agent.py) uses an explicit plan-and-act loop, with a reflect step added in and a step counter to keep it on track.

The controller behaves as follows: Given a top-level task, there are three basic actions:

1. **plan**: generate a natural language plan to achieve the task. Unlike the Magentic-One orchestrator, also maintain a step counter for which step you're on (initial value \= 1\)

Then given a plan, iterate an act-reflect "inner loop"

2. **act**: generate and execute Python code for the current step you're on. The act step has three parts:  
     
   * **ask**: Use the current plan step (autonomous), as the next thing to do (or ask the user, in interactive mode)  
   * **think**: Ask GPT to generate a thought (NL) and code (Python) that implements this step  
   * **execute**: Execute the code in a Python shell, and collect the observations.

3. **reflect**: reflect on the last action, and decide what to do next:

   * **done**: if the overall task is complete. This ends the experimental run.
   * **next_step**: if the current step is complete. This moves us to work on the next step in the plan.
   * **continue**: if the current step made progress, but something was missed or the code did not do the right thing. This moves us to take additional actions to complete the step.
   * **debug**: if a Python error message appeared. This will cause us to debug and retry the step.
   * **abort_shortcuts**: if shortcuts were taken. This causes the plan to be abandoned (can switch this behavior off with run_panda(allow_shortcuts=True)).
   * **abort_impossible**: if the plan appears logically impossible to succeed.
   * **replan**: if the current plan doesn't seem to be going anywhere. This will trigger abandoning the current plan and replanning from the current state.
   * **retry_earlier_step**: if current evidence suggests a problem with an earlier step, jump back to that step and try again from there.

The step counter ensures that the plan is followed systematically without skipping steps or hallucinating new steps. Finally, as the very first step, the system first strategizes as to whether to **plan**, or just jump straight into an **act** step (for simple questions).

![Panda agent controller](./panda.jpg)

# Repository Structure

* output/  directory in which an experiment-<date>-<time> subdirectory is created for each experiment run. The subdirectory will contain:
    * experiment.{txt,html} - The final report (txt/html format)
    * experiment-{trace,trace-long}.txt - Trace of the system running (what that the user sees/verbatim dialog between Panda and the LLM)
    * experiment.{py,-artifacts.py} - the Python code and Python artifacts (variable values) created during experimentation
    * experiment-done.txt - One-word flag showing the outcome of the experiment ("done", "abort_<failure_mode>")
    * Other files (e.g., .jpg, .png) - Experiment-specific files generated during experimentation (e.g., plots)
* output_demo/   contains an example of generated reports (html and txt versions) and execution traces
* evaluation\_output/     this directory will be created on demand to place the evaluation results in
* panda/     the Python codebase
  * panda_agent/    implements the agent controller  
    * panda\_agent.py is the agent controller
    * panda\_agent\_prompt.txt is the system prompt  
    * panda\_agent\_subprompts.py contains prompt addendums depending on which mode the agent is in (planning, acting (coding), reflecting)
    * paper\_writer.py, format\_categories.py, format\_dataset.py contain Python utilities for writing the final report, and also outputing the dialog trace files
  * utils/ contains a few shared basic Python utilities used by both researchworld and panda\_agent
  * evaluate/        contains utilities to run and score Panda on a dataset
    * run_evaluation.py             Run an evaluation (.csv dataset). Results placed in evaluation\_output/ by default
    * score_answer.py               Function to score answers returned by Panda run_evaluation() function    
    * run_astabench_evaluation.py   Run an evaluation (.json (ASTABench) dataset). Results placed in astabench/ by default.
    * astabench\_tiny\_tasks.csv    A toy .csv dataset
  
# Revision History:

 * v1.2: Addition of evaluate.pl to run evaluations, (with a toy and larger datasets in panda/evaluate/norabench*.csv files)
 * v1.3: Code refactoring, make panda a package. Renamed top-level call to run_panda()
 * v1.4: Add superpanda (iterative experiments) capability
 * v1.4.3: Add in some literature search tools (see panda/researchworld/lit_search.py) - these are currently not fully linked into Panda
 * v1.4.4: Add in panda/evaluate/run_astabench_evaluation.py for running ASTAbench tasks
 * v1.4.5: Restructure package, remove relative imports
 * v1.4.6: Package result outputs into a subdirectory, bug fixes
 * v1.4.8: Rename package as Panda ("plan-and-act")
 * v1.4.9: Add MCP interface (panda/mcp_server.py) and command line execution (python run_panda.py "What is 1 + 1?")
 * v1.4.10: Add superpanda_interactive.py (exploratory), minor code updates
 * v1.5: Remove researchworld and built-in research functions (not needed, can bias against good research decisions)
 * v1.5.1: Remove evaluation code (not strictly part of Panda itself)

# Questions, Issues, and Further Information

Contact Peter Clark (peterc@allenai.org)

  
