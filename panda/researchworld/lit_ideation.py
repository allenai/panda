"""
# 
import panda.panda_agent.lit_ideation.ideate_tasks_for_topic("

 ======================================================================
 	IDEATION FROM THE LITERATURE
 ======================================================================
Ideation tools: (returns LIST of task_json, with fields: {task:, rationale:, expected_results:, potential_impact:, plan:, likelihood:, significance:, corpus_ids:}
  ideate_task_from_paper(corpus_id)
  ideate_tasks_from_papers(topic, corpus_ids, n_tasks)     - returns task_list
  ideate_tasks_for_topic(topic, n_papers, n_tasks)         - returns task_list
  ideate_tasks_for_topics_to_csvfile(topics, n_papers, n_tasks, outfile="norabench_tasks.csv")  # create a NoraBench dataset. n_tasks = tasks per topic

A corpus_id can be either an arXivID or a S2CorpusId

  panda.researchworld.lit_ideation.ideate_task_from_paper("2410.13648")	# Yuling's ToM paper
  panda.researchworld.lit_ideation.ideate_tasks_from_papers("Theory of mind",["2410.13648", "253098632"], n_tasks=2)
  panda.researchworld.lit_ideation.ideate_tasks_for_topic(topic="Theory of mind", n_papers=3, n_tasks=2)
  panda.researchworld.lit_ideation.ideate_tasks_for_topics_to_csvfile(["Theory of Mind"], n_papers=10, n_tasks=10, outfile="tmp_tom.csv")  
  panda.researchworld.lit_ideation.ideate_tasks_for_topics_to_csvfile(INTERESTING_TOPICS, n_papers=10, n_tasks=10, outfile="new_dataset.csv")  # -> 100 tasks

------------------------------

A task is represented as a JSON of the form:
    {'task':TASK, 'rationale':RATIONALE, 'expected_results':RESULTS, 'potential_impact':IMPACT, 'plan':PLAN, 'likelihood':LIKELIHOOD, 'significance':SIGNIFICANCE}

LIKELIHOOD is GPT's guess of the likelihood that the expected_results will occur ["almost_certain", "likely", "probably", "unsure", "unlikely"]
   NOTE: The less certain GPT is of the outcome, the more interesting the task.
SIGNIFICANCE is a GPT estimate of the significance/utility of the research , one of ["very_low", "low", "medium", "high", "very_high"]

Ideation is conditioned on Panda's capabilities, i.e., it asks GPT to propose tasks Panda can actually do.
This is done by pre-pending the Panda SYSTEM_PROMPT in the query to GPT, so GPT sees the available Panda tools.
"""

import csv

from .lit_search import find_paper_ids, get_paper_text, summarize_paper
from panda.utils import call_llm_json, jprint

# ----------    

# list of useful topics for testing ideate_tasks_for_topics_to_csvfile above                
INTERESTING_TOPICS = [
    "To what extent to LMs have a 'theory of mind'?", \
    "Which LMs show greatest reasoning ability?", \
    "How well can LMs translate to other languages?", \
    "How sensitive are LMs to the prompts they are given?", \
    "Are LMs able to accurately judge confidence in their answers?", \
    "How well can LMs change speaker style?", \
    "Are the failure modes of different LMs similar or different?", \
    "Do LMs exhibit the same failure modes as humans?", \
    "How well are LMs able to make moral judgements?"]

# ----------------------------------------
#	1. IDEATE FROM A SINGLE PAPER
# ----------------------------------------

# ideate_task_from_paper("2410.13648")	# Yuling's ToM paper
def ideate_task_from_paper(corpus_id):
    paper_text = get_paper_text(corpus_id)
    prompt = task_ideation_prompt(paper_text)
    dialog = [prompt]
    print(f"Ideating a task based on paper paper:{corpus_id}...")        
    task_json, task_str = call_llm_json(dialog)
    print("Task:\n", task_str, "\n----------------------------------------\n")
    return task_json

# ----------

# tasks is destructively updated
def order_tasks(tasks, printout=False):
    score_tasks(tasks)
    tasks.sort(key=lambda item:item['score'], reverse=True)  # Sorts in descending order
    if printout:
        i = 0
        for task in tasks:
            i += 1
            print(f"TASK {i}\n")
            jprint(task)
            print("--------------------------")
    return tasks

# ----------    

# score = unsure outcome is highest, then 2nd order by significance
def score_tasks(tasks):
    for task in tasks:
        likelihood = task['likelihood']
        significance = task['significance']
        try:
            likelihood_score = LIKELIHOODS.index(likelihood)	# 0 (obvious) to N (very unlikely)
        except ValueError:
            print(f"ERROR! Unrecognized likelihood value '{likelihood}' - scoring it 0")
            likelihood_score = 0
        try:
            significance_score = SIGNIFICANCES.index(significance)	# 0 (insignificant) to N (very significant)
        except ValueError:
            print(f"ERROR! Unrecognized significance value '{significance}' - scoring it 0")
            significance_score = 0
        score = likelihood_score*10 + significance_score		# new: unsure is most important
        task['score'] = score

# ----------------------------------------
#	2. IDEATE FROM MULTIPLE PAPERS
# ----------------------------------------

"""
def ideate_tasks_from_papers(topic, corpus_ids:list[str], n_papers:int=10, n_tasks:int=3, prompt:str=None):
Purpose:
    Given one or more papers, ideate one or more tasks suitable for research using summaries of those papers
    *and* the information in the conversation so far.
    NOTE: proposed tasks are conditioned on the capabilities of Panda (the Panda SYSTEM_PROMPT is prepended to the GPT call)
Args:
    topic (str): The topic area for ideation
    corpus_ids (List(str)): A list of the paper IDs of the papers to ideate from, e.g., "2410.13648"
    n_tasks (int): The maximum number of tasks to suggest
    prompt (str): An optional prompt to help guide the ideator as to what kind of task to suggest.
Returns:
    tasks (list(dict)): A list of n_tasks tasks, each a JSON dict with keys: 
                        task, rationale, expected_results, potential_impact, plan, likelihood, significance, corpus_ids
                        Note: tasks is ordered, most "interesting" (least certain outcome, then impact) first
Example:
    print(ideate_tasks_from_papers("theory of mind", ["2310.15421","2302.08399","2401.08743v1"], 3))
->  [{'task': 'Develop a benchmark for evaluating Machine Theory of Mind using counterfactual reasoning',
      'rationale': "The papers suggest that current LLMs struggle with tasks requiring understanding...",
      'expected_results': 'LLMs may show some ability to handle counterfactuals....'
      'potential_impact': 'Improving counterfactual reasoning in AI could lead to...'
      'plan': {'plan': [{'step_number': 1, 'step': "Generate...}]}}
     {'task': 'Investigate the role of explicit mental state verbs in improving LLM performance on ToM tasks',...},
     {'task': 'Create a multimodal dataset to test Theory of Mind by combining text-based scenarios...}]
"""
def ideate_tasks_from_papers(topic, corpus_ids:list[str], n_papers:int=10, n_tasks:int=3, prompt:str=None):
    from ..panda_agent.panda_agent import SYSTEM_PROMPT, build_system_prompt	# on demand
    if not SYSTEM_PROMPT:
        SYSTEM_PROMPT = build_system_prompt()
    dialog = [SYSTEM_PROMPT]

#   print("DEBUG:corpus_ids =", corpus_ids)

    summaries = []
    used_corpus_ids = []
    for corpus_id in corpus_ids:				# new: We gather more than n_papers corpus_ids, on the grounds that several won't have summaries
        summary = summarize_paper(corpus_id)
        if summary:						# Note: a null summary "" will fail this test
            summaries.append(summary)
            used_corpus_ids.append(corpus_id)
            if len(summaries) >= n_papers:
                break
    
    additional_prompt = f"Here is some additional guidance as to what type of tasks to suggest:\n{prompt}\n" if prompt else ""
    initial_ideation_prompt = task_ideation_from_summaries_prompt(topic, summaries, additional_prompt)

    tasks = []

    for i in range(1,n_tasks+1):
        ideation_prompt = initial_ideation_prompt if i == 1 else NEXT_IDEATION_PROMPT

        dialog += [ideation_prompt]
        print(f"Ideating task {i}...")
        task_json, task_str = call_llm_json(dialog)
        dialog += [task_str]

        print("Assessing likelihood of expected_results...")
        dialog += [LIKELIHOOD_PROMPT]
        likelihood_json, likelihood_str = call_llm_json(dialog)
        dialog += [likelihood_str]
        likelihood = likelihood_json['confidence']

        print("Assessing significance of the task...")
        dialog += [SIGNIFICANCE_PROMPT]
        significance_json, significance_str = call_llm_json(dialog)
        dialog += [significance_str]
        significance = significance_json['significance']

        task_json['topic'] = topic
        task_json['likelihood'] = likelihood
        task_json['significance'] = significance
        task_json['corpus_ids'] = used_corpus_ids

#       print("Task:", task_json['task'])
        jprint(task_json)

        tasks += [task_json]

    return order_tasks(tasks)

# ----------              

NEXT_IDEATION_PROMPT = """Now suggest a different task, still on the same topic.
Make sure it is significantly different from the earlier tasks, for diversity. Use the same JSON format:
   {'task':TASK, 'rationale':RATIONALE, 'expected_results':RESULTS, 'potential_impact':IMPACT, 'plan':PLAN}
IMPORTANT: The task/plan should be implementable in Python, using the above or other functions. Don't suggest a task that requires skills that cannot be implemented, e.g., human studies. Don't suggest a task that requires access to external datasets, as you do not have access to them. Do not suggest tasks that involve pretraining or fine-tuning models, as you do not have the resources for such experiments."""

LIKELIHOOD_PROMPT = """
Now: How confident are you that the Expected Results above will occur?
 (a) almost_certain - you'd be stunned if they did not occur
 (b) likely - pretty sure they will occur
 (c) probably - they will probably occur, but there's a reasonable chance they will not
 (d) unsure - you've no idea whether the expected results will occur or not, it is a big unknown!
 (e) unlikely - they are unlikely to occur
Return with a JSON structure of the form:
  {"confidence": CONFIDENCE}
where CONFIDENCE is one of "almost_certain", "likely", "probably", "unsure", "unlikely"
"""

LIKELIHOODS = ["almost_certain", "likely", "probably", "unsure", "unlikely"]

SIGNIFICANCE_PROMPT = """
Finally: How significant/useful does this research seem?
 (a) very_low: the task is addressing an obscure, niche problem that almost no-one cares about 
 (b) low: the specific task is addressing a narrow area that only a few people care about
 (c) medium: The task might have some useful results that could help other people in their research
 (d) high: The task is addressing an important, unexplored area that many people would care about
 (e) very high: The task has hit on a broad, general problem that is of intense interest to many 
Return with a JSON structure of the form:
  {"significance": SIGNIFICANCE}
where SIGNIFICANCE is one of "very_low", "low", "medium", "high", "very_high"
"""

SIGNIFICANCES = ["very_low", "low", "medium", "high", "very_high"]

# ----------------------------------------
#	3. IDEATE TASKS FROM A TOPIC
# ----------------------------------------

"""
def ideate_tasks_for_topic(topic:str, n_papers:int=20, n_tasks:int=10):
Purpose:
    Given a topic, ideate one or more tasks from the top n_papers about that topic
    This function simply combines find_papers and ideate_tasks_from_papers
Args:
    topic (str): The topic area for ideation
    n_papers (int): The number of papers about the topic to retrieve. Set n_papers=0 to ideate purely on the topic name
    n_tasks (int): The maximum number of tasks to suggest
Returns:
    tasks_json (list(dict)): A list of n_tasks tasks, each a JSON dict with keys: task, rationale, expected_results, potential_impact, plan, likelihood, significance, corpus_ids
Example:
    print(ideate_tasks_for_topic("theory of mind"))
->  [{'task': 'Develop a benchmark for evaluating Machine Theory of Mind using counterfactual reasoning',
      'rationale': "The papers suggest that current LLMs struggle with tasks requiring understanding...",
      'expected_results': 'LLMs may show some ability to handle counterfactuals....'
      'potential_impact': 'Improving counterfactual reasoning in AI could lead to...'
      'plan': {'plan': [{'step_number': 1, 'step': "Generate...}]}}
     {'task': 'Investigate the role of explicit mental state verbs in improving LLM performance on ToM tasks',...},
     {'task': 'Create a multimodal dataset to test Theory of Mind by combining text-based scenarios...}]
"""
def ideate_tasks_for_topic(topic:str, n_papers:int=10, n_tasks:int=10):
    print("Searching for papers on topic:", topic, "...")
    corpus_ids = find_paper_ids(topic, n_papers*3)	# -> [{'corpus_id':...,'title':...},...] - *3 as many won't be downloadable
    return ideate_tasks_from_papers(topic, corpus_ids, n_papers=n_papers, n_tasks=n_tasks)	# returns tasks

# ----------------------------------------
#	4. IDEATE TASKS FROM MULTIPLE TOPICS (and write to a ile)
# ----------------------------------------

DATASET_COLUMNS = ['tid','topic','corpus_ids', 'task','rationale','expected_results','potential_impact','plan','json']

# This is a simple loop around tasks_for_topic, and write out a CSV of topics, corpus_ids, and tasks. Useful for building a NoraBench test suite!
# Set n_papers=0 to ideate purely on the topic name

### ideate_tasks_for_topics_to_csvfile(["theory of mind"], 2, 2)
### ideate_tasks_for_topics_to_csvfile(INTERESTING_TOPICS, 8, 8)
### ideate_tasks_for_topics_to_csvfile(INTERESTING_TOPICS, n_papers=0, n_tasks=5)  # n_tasks = tasks per topic
def ideate_tasks_for_topics_to_csvfile(topics, n_papers=10, n_tasks=10, outfile="norabench_tasks.csv"):
    # Initialize the file
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(DATASET_COLUMNS)    

    for i in range(0, len(topics)):
        topic = topics[i]
        print("Topic ", i+1, ": ", topic, sep="")
        tasks = ideate_tasks_for_topic(topic, n_papers=n_papers, n_tasks=n_tasks)
        save_tasks_to_csvfile(topic, tasks, outfile)

# ----------        

def save_tasks_to_csvfile(topic, tasks, outfile):
    tid = get_highest_id(outfile)			# creates outfile if needed too
    with open(outfile, 'a', newline='') as my_csvfile:
        fieldnames = DATASET_COLUMNS
        writer = csv.DictWriter(my_csvfile, fieldnames=fieldnames)
        for task in tasks:
            tid += 1
            task['tid'] = tid
            task['topic'] = topic		# add topic into the output
            row = {key: task.get(key, "") for key in fieldnames}  # Handle missing keys
            row['json'] = task
            writer.writerow(row)

# ----------

# Generate an unused TaskID number
def get_highest_id(outfile):
    try:
        with open(outfile, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            highest_id = 0  # Initialize to 0 (in case the file is empty after header)
            for row in reader:
                try:
                    current_id = int(row['tid'])
                    if current_id:
                        highest_id = max(highest_id, current_id)
                except (ValueError, IndexError) as e:
                    print(f"Warning: Invalid data in CSV: {row}. Skipping. Error: {e}")
            return highest_id

    except FileNotFoundError:
        with open(outfile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(DATASET_COLUMNS)
        return 0  # Return 0 as the highest tid for the new ile

### ======================================================================
###		PROMPT LIBRARY FOR THE ABOVE
### ======================================================================                

# ----------------------------------------
#  PROMPT 1: IDEATE FROM A SINGLE PAPER (full text)
# ----------------------------------------

def task_ideation_prompt(paper_text):
    from ..panda_agent.panda_agent import SYSTEM_PROMPT, build_system_prompt	# on demand
    if not SYSTEM_PROMPT:
        SYSTEM_PROMPT = build_system_prompt()
    prompt = SYSTEM_PROMPT + """
Now read the following paper:
======================================================================
                   START OF PAPER
======================================================================
""" + paper_text + """
======================================================================
                   END OF PAPER
======================================================================

Now: Suggest a new top-level research task that follows on from this prior work, to explore some new, related idea suggested by this paper. Do not suggest a task that simply replicates the experiments in the paper. Rather, consider what new, open questions are posed by this paper, and then suggest a task and plan to address one of those questions. 

Provide the following:
1. task: The new task that you're proposing
2. rationale: Describe what open questions the paper poses or suggests, and how the new task addresses one of those questions.
3. expected_results: Describe what results you are expecting.
4. potential_impact: Describe how this new research might advance the science, if succcessful.
5. plan: Describe a plan to perform this top-level task. 

IMPORTANT: The task/plan should be implementable in Python, using the above or other functions. Don't suggest a task that requires skills that cannot be implemented, e.g., human studies. Don't suggest a task that requires access to external datasets, as you do not have access to them. Do not suggest tasks that involve pretraining or fine-tuning models, as you do not have the resources for such experiments.

Return your answer in a JSON structure of the form:
    {"task":TASK, "rationale":RATIONALE, "expected_results":RESULTS, "potential_impact":IMPACT, "plan":PLAN}
where TASK, RATIONALE, RESULTS, and IMPACT are strings
and PLAN is itself a JSON structure of the form [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]

Now go ahead!
"""
    return prompt

# ----------------------------------------
#  PROMPT 2: IDEATE FROM MULTIPLE PAPERS (paper summariees)
# ----------------------------------------

def task_ideation_from_summaries_prompt(topic, summaries, additional_prompt):
    from ..panda_agent.panda_agent import SYSTEM_PROMPT, build_system_prompt	# on demand
    if not SYSTEM_PROMPT:
        SYSTEM_PROMPT = build_system_prompt()
        
    prompt = SYSTEM_PROMPT + f"""
I'm looking for a new research idea on the topic of: {topic}
Now read the following paper summaries:
======================================================================
                   START OF SUMMARIES
======================================================================
""" + "\n".join(summaries) + """
======================================================================
                   END OF SUMMARIES
======================================================================
"""
    prompt += "Now: Suggest a new, top-level research task on the topic of: " + topic + """
The task should follows on from the prior work described (if any), and explore a new, related idea suggested by these papers. Do not suggest a task that simply replicates the experiments in the papers. Rather, consider what new, open questions are posed by these papers, and then suggest a task and plan to address one of those questions. 
""" + additional_prompt + """
For the task you suggest, return the following:
1. task: The new task that you're proposing
2. rationale: Describe what open questions the paper poses or suggests, and how the new task addresses one of those questions.
3. expected_results: Describe what results you are expecting.
4. potential_impact: Describe how this specific research might advance the science, if succcessful.
5. plan: Describe a plan to perform this top-level task. 

IMPORTANT: The task/plan should be implementable in Python, using the above or other functions. Don't suggest a task that requires skills that cannot be implemented, e.g., human studies. Don't suggest a task that requires access to external datasets, as you do not have access to them. Do not suggest tasks that involve pretraining or fine-tuning models, as you do not have the resources for such experiments.

Return your answer in a JSON structure of the form:
   {'task':TASK, 'rationale':RATIONALE, 'expected_results':RESULTS, 'potential_impact':IMPACT, 'plan':PLAN}
where TASK, RATIONALE, RESULTS, and IMPACT are strings
and PLAN is itself a JSON structure of the form [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]
"""
    return prompt
