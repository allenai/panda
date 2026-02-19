"""
With Chaz help: https://chatgpt.com/share/68ed7039-de3c-8001-9bb0-99ed80553967

Panda signature:
def run_panda(task=None, plan=None, background_knowledge=None, force_report=False, thread_id=None, reset_namespace=True, allow_shortcuts=False, model=agent_config.PANDA_LLM, reset_dialog=True, outputs_dir="output"):

Usage:
% python run_panda.py "What is 1 + 1?" [--force_report] [--outputs_dir "subdir_of_panda"]
Optional arguments:
  --force_report     - force Panda to *always* write a report on its work
  --outputs_dir      - directory for the experimental results directory (containing report and other artifacts). Default is output/
"""

import argparse
import panda

def main():
    parser = argparse.ArgumentParser(description="Run Panda tasks from the command line.")
    parser.add_argument("task", help="The research or analysis question to run.")
    parser.add_argument("--task_file", help="A text file containing the research or analysis question to run.")
    parser.add_argument("--background_knowledge", default=None, help="Additional context for the task.")
    parser.add_argument("--no_force_report", action="store_false", dest="force_report", help="If set, do not force a report.")    
#   parser.add_argument("--force_report", action="store_true", help="If set, always return a report under all circumstances.")
    parser.add_argument("--outputs_dir", default="output", help="Where to place the experiment artifacts, relative to the Panda directory.")
    args = parser.parse_args()

    # Call into your package
    panda.run_panda(
        task=args.task,
        task_file=args.task_file,
        background_knowledge=args.background_knowledge,
        force_report=args.force_report,
        outputs_dir=args.outputs_dir
    )

if __name__ == "__main__":
    main()
