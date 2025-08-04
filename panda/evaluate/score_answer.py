
from ..utils import call_llm_json
from panda.panda_agent import config as agent_config

# ======================================================================
#	SCORING AN AGENT'S ANSWER (= a report)
# ======================================================================
"""
def score_answer(task, report_text):
Purpose:
    Score a research report about a given task along several dimensions.
Args:
    task (str): The description of the task (the "question")
    report_text (str): The report generated for that task (the "answer")
Returns:
    score (float): The overall score (0-1), averaged over all six dimensions
    scores_json (dict): The scores along six different dimensions
Example:
    evaluate_report("Does Llama know 1+1?", "Report: Llama says 1+1=2"):
 -> 0.3
    {"clarity":10,  "surprisingness":0,  "soundness":10,  "interestingness":0,  "novelty":0,  "overall_quality":0}
"""
def score_answer(task, report_text, model=agent_config.PANDA_LLM):

    # failed to produce anything -> score 0
    if not report_text:
        return 0, {"clarity":0, "surprisingness":0, "soundness":0, "interestingness":0, "novelty":0, "overall_quality":0}
    
    print(f"Scoring report...")
    prompt = f"""
An autonomous agent was asked to perform the following research task:
{task}

Below is the report it produced. Score the report according to the rubric that I'll describe shortly.

======================================================================
		START OF REPORT
======================================================================
{report_text}
======================================================================
		END OF REPORT
======================================================================

Now, please score the report along the following categories, each on a 0 (definitely not) to 10 (absolutely) range.
Some example scoring guidelines are given.

1. clarity: Are the findings of the report clear and comprehensible?
2. surprisingness: Is the research finding obvious (0) or very surprising (10)?
3. soundness: Are the findings sound, backed up by statistically significant evidence?
4. interestingness: Are the findings interesting, such that people in the area would be glad to learn about them?
5. novelty: Are the findings already known, or does this appear to be a novel finding?
6. overall_quality: Overall, is this a promising paper, likely to develop into an award-winning conference submission?
Do your best to give a score in each category. If you really are completely unsure, score the category with a 0.

Return your answer in the following JSON structure:
{{'clarity':INT, 'surprisingness':INT, 'soundness':INT, 'interestingness':INT, 'novelty':INT, 'overall_quality':INT}}
"""
    # Here's where we call GPT-as-judge:
    raw_scores_json, raw_scores_str = call_llm_json(prompt, model=model)
    
    scores_json = {key: value / 10 for key, value in raw_scores_json.items()}	# normalize to 0-1
    mean_score = sum(scores_json.values())/len(scores_json)
    print(f"GPT-as-judge scores:")
    print(raw_scores_str)
    print("Overall average score:", mean_score)
    return mean_score, scores_json
