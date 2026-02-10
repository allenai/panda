
#======================================================================
#	STRATEGIZE SUBPROMPT
#======================================================================

# remove "partial plan" (explore) option for now
STRATEGY_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Reflect on the immediate task, and decide on the appropriate strategy to follow, one of:
 - do: a task you understand and can do directly in Python, with one or a few commands
 - plan: a larger but well-defined task, that you can generate a plan for (then subsequently follow)

Answer with a JSON structure of the form: {"strategy":STRATEGY, "explanation": EXPLANATION}, where 
 - STRATEGY is either "do" or "plan"
 - EXPLANATION is a natural-language explanation
"""

'''
STRATEGY_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Reflect on the immediate task, and decide on the appropriate strategy to follow, one of:
 - do: a task you understand and can do directly in Python, with one or a few commands
 - plan: a larger but well-defined task, that you can generate a plan for (then subsequently follow)
 - explore: a poorly defined task, where you need to take some exploratory steps and then reflect on what to do next

Answer with a JSON structure of the form: {"strategy": "do" OR "plan" OR "explore", "explanation": "..."}
"""
'''

#======================================================================
#	 PARTIAL_PLAN (EXPLORE) SUBPROMPT
#======================================================================

# **NOTE** Partial planning no longer used (commented out in panda_agent.py)

PARTIAL_PLAN_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Generate a partial plan - one or more initial steps - to get started on this task.
The partial plan should specify initial explorations / data gathering operations to help you get started.
As the full plan will depend on the results from those initial steps, you don't (and can't) generate the full plan right now.

The last step of your partial plan should be exactly "Plan what to do next".
I'll then execute the partial plan. When we reach that last step, we'll decide from there what should follow!

Return your partial plan as a JSON object with the following structure:
{"plan": [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]}
"""

#======================================================================
#	 CONTINUE_PLAN SUBPROMPT (follows completion of PARTIAL_PLAN)
#======================================================================

# **NOTE** Partial planning no longer used (commented out in panda_agent.py)

CONTINUE_PLAN_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Now that you've completed the partial plan, generate either:
 - a complete new plan to finish the top-level task, or
 - another partial plan to continue to make progress on the top-level, describing the next few steps (even if it does not complete the top-level task).

If you chose to generate a partial plan, make sure that the last step is exactly "Plan what to do next".

Return your plan as a JSON object with the following structure:
{"plan": [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]}
"""

#======================================================================
#	PLAN_DESIGN_DECISIONS SUBPROMPT
# [EXPERIMENTAL]
#======================================================================

PLAN_DESIGN_DECISIONS_SUBPROMPT = """
YOUR NEXT INSTRUCTION: You will shortly be asked to generate a plan to perform this research. 
However, BEFORE doing that, in preparation for making an actual plan, first identify the key 
design decisions that are needed for research plan, and recommendations about which option to choose.

(Avoid plans that involve human labeling, verification, etc. as you are not able to interact with humans).

Return your list of design decisions as a JSON object with the following structure:
{"design_decisions": [{"number":1, "design_decision":DESCRIPTION, "recommendation":RECOMMENDATION}, {"number":2, ...}]}
"""

#======================================================================
#	PLAN SUBPROMPT
#======================================================================

PLAN_SUBPROMPT = """
YOUR NEXT INSTRUCTION: generate a plan to perform this research. 
Avoid steps that involve human labeling, verification, etc. as you are not able to interact with humans.
Return your plan as a JSON object with the following structure:
{"plan": [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]}
"""

#======================================================================
#	REPLAN SUBPROMPT
#======================================================================

REPLAN_SUBPROMPT = """
According to your last reflection, it looks like the current plan isn't working.

YOUR NEXT INSTRUCTION: Generate a revised plan to perform the research task.
You don't need to repeat steps that were already performed successfully, i.e., the new plan should start from the current state of your research, rather than start from scratch.
You can reuse variables and data structures from the earlier execution, if that is helpful.
I will then discard the old plan, and continue with your revised plan.
Avoid steps that involve human labeling, verification, etc. as you are not able to interact with humans.
Make sure your plan is DIFFERENT to the previous PLAN!! In particular, DO NOT REPEAT THE STEP THAT FAILED!

Return your revised plan as a JSON object with the following structure:
{"plan": [{"step_number":1, "step":DESCRIPTION}, {"step_number":2, "step":DESCRIPTION}, ....]}
"""

#======================================================================
#	ACTION SUBPROMPT
#======================================================================

ACTION_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Generate Python code that implements this step. I'll then execute it and show you the results. 
Avoid code, e.g., input(), that requires a response from the user.
Return your answer as a JSON object of the form:
      {"thought":THOUGHT, "action":PYTHON_CODE}
"""

#======================================================================
#	CONTINUE ACTION SUBPROMPT
#======================================================================

CONTINUE_SUBPROMPT = """
According to your last reflection, the step is only partially completed. 

YOUR NEXT INSTRUCTION: Generate Python code that completes this step. I'll then execute it and show you the results.
Return your answer as a JSON object of the form:
      {"thought":THOUGHT, "action":PYTHON_CODE}
"""

#======================================================================
#	DEBUG SUBPROMPT
#======================================================================

DEBUG_SUBPROMPT = """
According to your last reflection, there was a problem implementing/executing this step.

YOUR NEXT INSTRUCTION: Try again, and generate new Python code that implements this step. Pay particular
attention to avoid the problem that occurred last time. I'll then execute it and show you the results.
Return your answer as a JSON object of the form:
      {"thought":THOUGHT, "action":PYTHON_CODE}
"""

#======================================================================
#	REFLECT SUBPROMPT
#======================================================================

REFLECTION_SUBPROMPT = """
YOUR NEXT INSTRUCTION: Perform a REFLECTION step to assess if top-level task is complete, the current plan step is complete, if shortcuts were taken, etc.

Assess:
- thought: Summarize the progress made so far in the research, and what to do next
- task_complete: Have you achieved the top-level research task?
- current_step_complete: Have you successfully completed the current step in the plan? If you generated data or results, did you remember to print out the results so they are visible in the conversation history for future steps?
- software_bug: Did a Python error message occur when executing the code?
- took_shortcuts: Did you take a shortcut to completing the step, so the execution wasn't completely faithful? For example
     - You simulated an external database, system, or human, rather than actually using that resource (because it wasn't available)
     - You generated code containing stubs, rather than generating a completely operational piece of code
     - You guessed or approximated the result of a function, rather than actually executing it
     - You used some imagined or hypothetical values, rather than actual values derived from data
   Note: if the current step is incomplete, this does not automatically mean you took a shortcut - it just means you still have 
   some extra work to do on the current step.

And then: Tell me what the next TYPE of action should be (not the action itself). It should be one of:
 - "done": if the overall task is complete. This ends the experimental run.
 - "next_step": if the current step is complete. This moves us to work on the next step in the plan.
 - "continue": if the current step made progress, but something was missed or the code did not do the right thing. This moves us to take additional actions to complete the step.
 - "debug": if a Python error message appeared. This will cause us to debug and retry the step.
 - "abort_shortcuts": if shortcuts were taken. This causes the plan to be abandoned. It's important to abandon a plan if a shortcut was taken.
 - "abort_impossible": if the plan appears logically impossible to succeed.
 - "replan": if the current plan doesn't seem to be going anywhere. This will trigger abandoning the current plan and replanning from the current state.
 - {"action":"retry_earlier_step", "step_number":NUMBER, "revised_instructions":INSTRUCTIONS}
   This complex action tells us to redo an earlier plan setp (NUMBER), with revised instructions.
   This action is done if current evidence suggests a problem with an earlier step.
   The revised instructions should guide the system to (re)perform the earlier step in a way that avoids that problem.
   For example, if a generated dataset is too hard or too easy, we might go back and regenerate it with extra instructions about the appropriate difficulty level.

Return your response as a JSON structure of the form:
  {"thought": STRING, "task_complete": BOOLEAN, "current_step_complete": BOOLEAN, "software_bug": BOOLEAN, "took_shortcuts": BOOLEAN, "next_action":NEXT_ACTION}

NEXT_ACTION is one of: "done", "next_step", "continue", "debug", "abort_shortcuts", "abort_impossible", "replan", {"action":"retry_earlier_step", "step_number":NUMBER, "revised_instructions":INSTRUCTIONS}
"""

REFLECTION_SUBPROMPT_ALLOW_SHORTCUTS = """
YOUR NEXT INSTRUCTION: Perform a REFLECTION step to assess if top-level task is complete, the current plan step is complete, if shortcuts were taken, etc.

Assess:
- thought: Summarize the progress made so far in the research, and what to do next
- task_complete: Have you achieved the top-level research task?
- current_step_complete: Have you successfully completed the current step in the plan? If you generated data or results, did you remember to print out the results so they are visible in the conversation history for future steps?
- software_bug: Did a Python error message occur when executing the code?

And then: Tell me what the next TYPE of action should be (not the action itself). It should be one of:
 - "done": if the overall task is complete. This ends the experimental run.
 - "next_step": if the current step is complete. This moves us to work on the next step in the plan.
 - "continue": if the current step made progress, but something was missed or the code did not do the right thing. This moves us to take additional actions to complete the step.
 - "debug": if a Python error message appeared. This will cause us to debug and retry the step.
 - "replan": if the current plan doesn't seem to be going anywhere. This will trigger abandoning the current plan and replanning from the current state.
 - {"action":"retry_earlier_step", "step_number":NUMBER, "revised_instructions":INSTRUCTIONS}
   This complex action tells us to redo an earlier plan setp (NUMBER), with revised instructions.
   This action is done if current evidence suggests a problem with an earlier step.
   The revised instructions should guide the system to (re)perform the earlier step in a way that avoids that problem.
   For example, if a generated dataset is too hard or too easy, we might go back and regenerate it with extra instructions about the appropriate difficulty level.

Return your response as a JSON structure of the form:
  {"thought": STRING, "task_complete": BOOLEAN, "current_step_complete": BOOLEAN, "software_bug": BOOLEAN, "next_action":NEXT_ACTION}

NEXT_ACTION is one of: "done", "next_step", "continue", "debug", "replan", {"action":"retry_earlier_step", "step_number":NUMBER, "revised_instructions":INSTRUCTIONS}
"""

#======================================================================
#	REFLECT ON PLAN SUBPROMPT
#======================================================================

PLAN_REFLECTION_SUBPROMPT = """
YOUR NEXT INSTRUCTION: 
REFLECT on the plan you have just created, and assess whether it is doable using the Python functions available to you, plus general Python.
Note that plan is not doable if it requires:
 - accessing information on the Web (you don't have access)
 - human interaction (you are working autonomously)
 - pre-training or fine-tuning a model (you do not have these capabilities)

Return your answer as a JSON object with the following structure:
    {"doable": YESNO, "explanation": EXPLANATION}
where YESNO is one of the three strings: "yes" or "unsure" or "no", and EXPLANATION is the justification for that YESNO answer.
"""

PLAN_REFLECTION_SUBPROMPT_ALLOW_SHORTCUTS = """
YOUR NEXT INSTRUCTION: 
REFLECT on the plan you have just created, and how to make it doable using the Python functions available to you, plus general Python.
If there any tricky parts, e.g., accessing information on the Web, pretraining and fine-tuning a model, then think about how to
approximate or simulate those activities.

Return your answer as a JSON object with the following structure:
    {"doable": "yes", "explanation": EXPLANATION}
Note the value of "doable" should ALWAYS be "yes", with EXPLANATION providing details of how to make the plan doable.
"""

