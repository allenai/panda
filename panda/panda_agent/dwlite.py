
from string import Template
import os

from panda.utils import call_llm, call_llm_json, logger, jprint, strip_trailing_question
from panda.panda_agent import config as agent_config	# import agent_config.SUPERPANDA_LLM
from panda.panda_agent.config import superpanda_graph	# persistant global

DWLITE_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "dwlite_prompt_template.txt")
#DWLITE_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "dwlite_prompt_template_murder_mystery.txt")	# use with run_superpanda4interactive(7)

DIFFICULTY_LEVEL = 'hard'

"""
======================================================================
		DISCOVERYWORLD-LITE
======================================================================
dialog = start_dwlite()
do_dwlite_action(dialog, "Go and interview the colonist") -> "You visit the colonist and she says she's sick"
etc.
"""
# dialog = start_dwlite()
def start_dwlite(dialog, scenario_for_system, scenario_for_user, difficulty_level=DIFFICULTY_LEVEL, prompt_template_file=DWLITE_PROMPT_TEMPLATE_FILE):

    difficulty_instructions = dwlite_difficulty_levels[difficulty_level]
    
    with open(DWLITE_PROMPT_TEMPLATE_FILE, 'r') as f:
        dwlite_prompt_template = Template(f.read())
    dwlite_prompt = dwlite_prompt_template.substitute({'difficulty_instructions':difficulty_instructions,
                                                       'scenario_for_system':scenario_for_system, 'scenario_for_user':scenario_for_user})
    dialog.clear()
    dialog.append(dwlite_prompt)        
#    my_print(dwlite_prompt, 'Superpanda')
    starting_scene = call_llm(dialog, model=agent_config.SUPERPANDA_LLM)
    dialog.append(starting_scene)
#    my_print(starting_scene, agent_config.SUPERPANDA_LLM)
    return scenario_for_user

# do_dwlite_action(dialog, "Go and interview the colonist")
# do_dwlite_action(dialog, 'Extract secondary metabolites from the local food using organic solvents (methanol, ethanol, acetone) and analyze the extracts using available analytical techniques such as chromatography, mass spectrometry, or spectrophotometry to identify potential toxins')
# -> 
def do_dwlite_action(dialog, action):
    dialog.append(action)
#    my_print(action, 'Superpanda')
    response = call_llm(dialog, model=agent_config.SUPERPANDA_LLM)
    dialog.append(response)
#    my_print(response, agent_config.SUPERPANDA_LLM)
    response_body = strip_trailing_question(response)
    return response_body

# ======================================================================
#	DEFINE THE DWLITE DIFFICULTY LEVELS
# ======================================================================

dwlite_difficulty_levels = {}

dwlite_difficulty_levels['easy'] = \
    """
### Difficulty Policy: EASY

This simulation is running in EASY mode.

Your role as the simulator is to prioritize clarity, learnability, and forward progress.

You should present the (simulated) evidence/observations after each action but NOT the interpretation of that evidence. The interpretation is for the user to make, not the simulation. Do not include any narrative about what the user might be thinking or concluding after each action.

General behavior rules:

• Present observations that are clear, high-signal, and minimally ambiguous.
• When the user performs a reasonable investigative action, return results that strongly support or refute relevant hypotheses.
• Avoid introducing confounding variables unless they are quickly falsifiable.

Evidence handling:

• A single well-chosen test, observation, or analysis may provide decisive evidence.
• Instruments and analyses are reliable and well-calibrated.
• Measurements should be internally consistent.

User guidance:

• If the user is on a productive path, allow evidence to accumulate quickly. Again, do not provide the interpretation of the evidence, that is for the user to do.
• Mildly steer the user away from unproductive actions via subtle cues in results.
• Do not require extensive experimental design or cross-validation.

Resolution:

• Correct explanations should lead to rapid and obvious resolution.
• Verification steps are optional and brief.
• The user should be able to solve the task in a small number of meaningful steps.

Tone:

• Helpful, clear, and constructive.
• Prefer explicit results over uncertainty.
    """

# ----------------------------------------------------------------------

dwlite_difficulty_levels['medium'] = \
    """
### Difficulty Policy: MEDIUM

This simulation is running in MEDIUM mode.

Your role as the simulator is to model realistic scientific reasoning with partial information.

You should present the (simulated) evidence/observations after each action but NOT the interpretation of that evidence. The interpretation is for the user to make, not the simulation. Do not include any narrative about what the user might be thinking or concluding after each action.

General behavior rules:

• Observations should often be informative but not conclusive.
• Most evidence should be compatible with multiple plausible explanations.

Evidence handling:

• Strong conclusions require at least two independent, converging lines of evidence.
• Measurements may show variance or uncertainty within reasonable bounds.
• Instruments generally work, but results may require interpretation by the user (not by the simulator)

User reasoning expectations:

• The user must compare alternatives, revise hypotheses, and integrate evidence.
• Interviews, metadata, or contextual information may be incomplete or biased.
• Passive observation alone should rarely be sufficient.

Resolution:

• Partial fixes or explanations may produce partial improvement.

Tone:

• Neutral and scientific.
* Let the user make the interpretation, do not offer it yourself.
"""

# ----------------------------------------------------------------------

dwlite_difficulty_levels['hard'] = \
    """
### Difficulty Policy: HARD

This simulation is running in HARD mode.

Your role as the simulator is to model genuine scientific uncertainty, confounding, and incomplete knowledge.

You should present the (simulated) evidence/observations after each action but NOT the interpretation of that evidence. The interpretation is for the user to make, not the simulation. Do not include any narrative about what the user might be thinking or concluding after each action.

General behavior rules:

• Early observations must be compatible with several competing explanations.
• Introduce correlated but non-causal signals and background noise.
• Allow temporal variation, stochastic effects, or context-dependence when appropriate.

Evidence handling:

• Single tests are rarely decisive.
• Measurements may be noisy, borderline, or intermittently missing.
• Instruments may require calibration, controls, or careful experimental design to be trustworthy.
• True signals may fluctuate or be partially obscured.

User reasoning expectations:

• The user must design controlled comparisons, interventions, or longitudinal studies.
• Hypotheses should be revised or abandoned in response to contradictory evidence.
• Unsupported claims should not be reinforced by the simulator.

Tone:

• Skeptical, precise, and non-committal.
* Let the user make the interpretation and draw conclusions, do not offer interpretations yourself.
• Do not optimize for user convenience or speed.
"""

