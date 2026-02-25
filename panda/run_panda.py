"""
With Chaz help: https://chatgpt.com/share/68ed7039-de3c-8001-9bb0-99ed80553967

Panda signature:
def run_panda(task=None, plan=None, background_knowledge=None, force_report=False, thread_id=None, reset_namespace=True, allow_shortcuts=False, model=agent_config.PANDA_LLM, reset_dialog=True, outputs_dir="output"):

Usage:
% conda activate panda
(panda) % python -m panda.run_panda--task "What is 1 + 1?" [--force_report] [--outputs_dir "subdir_of_panda"]
Optional arguments:
  --force_report     - force Panda to *always* write a report on its work
  --outputs_dir      - directory for the experimental results directory (containing report and other artifacts). Default is output/

Or install as a tool:
% uv tool install git+https://github.com/allenai/panda --force
	# executable placed in %USERPROFILE%/Users/peter/.local/bin [PC]  ~/.local/bin [Mac]
	# source files are placed in %USERPROFILE%/AppData/Local/uv/tools/
% panda --task "What is 1 + 1?"
"""

import argparse
#import panda
from .panda_agent import run_panda	# import the function (not this file!)

def main():
    parser = argparse.ArgumentParser(description="Run Panda tasks from the command line.")
    parser.add_argument("--task", help="The research or analysis question to run.")
    parser.add_argument("--task_file", default=None, help="A text file containing the research or analysis question to run.")
    parser.add_argument("--background_knowledge", default=None, help="Additional context for the task.")
    parser.add_argument("--background_knowledge_file", default=None, help="A text file containing additional context for the task.")    
    parser.add_argument("--force_report", action="store_true", help="If set, always return a report under all circumstances.")
    parser.add_argument("--outputs_dir", default="output", help="Where to place all experiments artifacts, relative to the Panda directory.")
    parser.add_argument("--experiment_subdir", default=None, help="Where to place this specific experiment's artifacts, relative to the Panda directory.")
    parser.add_argument("--result_file", default=None, help="Where to place the JSON result.")
    args = parser.parse_args()

    # Call into your package
    run_panda(
        task=args.task,
        task_file=args.task_file,
        background_knowledge=args.background_knowledge,
        background_knowledge_file=args.background_knowledge_file,                
        force_report=args.force_report,
        outputs_dir=args.outputs_dir,
        experiment_subdir=args.experiment_subdir,
        result_file=args.result_file
    )

if __name__ == "__main__":
    main()
