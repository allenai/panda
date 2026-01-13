"""
superpanda.py: the original (finding -> mechanism -> test -> experiment)
superpanda2: Simply generates a tree (formatted in HTML) of quest -> mechanisms -> tests (set per mechanism) to envision the search space
superpanda3.py - does a decision-theoretic estimated value of information (EVOI) to select the next action to perform,
    by computing from a representation of hypotheses, evidence, and the expected value of flipping hypotheses T/F.
    There's an underlying JSON "graph" representation of the E and H (it's really jut a row of E and a row of H connected).
superpanda4.py: Automated DW, using a belief graph representation of H, I, O (evidence) - see superpanda4_initial_prompt_template3.txt for details
superpanda4interactive.py: Interactive version (user-driven)

Written with extensive help from Chaz: https://chatgpt.com/share/69277521-10a8-8001-882e-2ca05c2b5225

%load_ext autoreload
%autoreload 2 
import panda

panda.panda_agent.superpanda_interactive.run_superpanda_interactive(8)

# %run -i panda/panda_agent/superpanda_interactive.py
# %run -i panda/panda_agent/dwlite_quests.py
# %run panda/panda_agent/animate.py

# BUILD a toy graph
run_superpanda_interactive(0)
run_superpanda_interactive("murder")
continue_superpanda4()		# continue from where we left off. This relies on 4 globals storing the state: superpanda_dialog, dwlite_dialog, belief_graph, and results_dir

showme("H1", belief_graph)      # view a node/edge in the graph

# ======================================================================
"""

from __future__ import annotations

import os
import html
import json

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from string import Template
from graphviz import Digraph				# Render a DOT file
from pathlib import Path				# for create_next_dir()

from panda.utils import call_llm, call_llm_json, logger, jprint, strip_trailing_question
from panda.panda_agent import config as agent_config	# import agent_config.SUPERPANDA_LLM

from panda.panda_agent.config import superpanda_graph	# persistant global
from panda.panda_agent.dwlite import start_dwlite, do_dwlite_action
from panda.panda_agent.dwlite_quests import dwlite_quests
from panda.panda_agent.animate import make_video

SUPERPANDA_INITIAL_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "superpanda_interactive_initial_prompt_template.txt")
SUPERPANDA_FOLLOWUP_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "superpanda_interactive_followup_prompt_template.txt")

SOLUTION_THRESHOLD = 95

### ======================================================================
###                MAIN SYSTEM
### ======================================================================
"""
E:people are sick -----> [H1:..., ..., Hn:...]
"""

def run_superpanda_interactive(quest_id=0):

    global superpanda_dialog
    global dwlite_dialog
    global belief_graph
    global results_dir

    # ====================
    # Read Superpanda prompt templates:
    # ====================    

    with open(SUPERPANDA_INITIAL_PROMPT_TEMPLATE_FILE, 'r') as f:
        superpanda_initial_prompt_template = Template(f.read())

    results_dir = create_next_dir()
    print("Results dir", results_dir, "created!")

    # ====================
    # Start DWLite
    # ====================

    if quest_id == "murder":			# murder-mystery
        quest = generate_murder_mystery()
        DWLITE_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "dwlite_prompt_template_murder_mystery.txt")        
    else:
        quest = dwlite_quests[quest_id]			# imported from dwlite_quests.py
        DWLITE_PROMPT_TEMPLATE_FILE = os.path.join(agent_config.MODULE_DIR, "dwlite_prompt_template.txt")

    # write the quest out to files in the directory        
    quest_json_file = os.path.join(results_dir, "quest.json")
    quest_txt_file = os.path.join(results_dir, "quest.txt")
    quest_json_str = json.dumps(quest, indent=2)
    quest_txt = quest_json_str.replace("\\n", "\n")

    with open(quest_json_file, "w", encoding="utf-8") as f:
        f.write(quest_json_str)
    with open(quest_txt_file, "w", encoding="utf-8") as f:
        f.write(quest_txt)

    scenario_for_system = quest['scenario_for_system']
    scenario_for_user = quest['scenario_for_user']

    dwlite_dialog = []
    init_interaction = start_dwlite(dwlite_dialog, scenario_for_system, scenario_for_user, prompt_template_file=DWLITE_PROMPT_TEMPLATE_FILE) # init_observation = scenario_for_user (or should be!)

    # Build initial belief graph
    belief_graph = {'nodes':[{'id':"I1", 'type':"interaction", 'title':"initial scenario", 'description':init_interaction}], 'edges':[]}

    # ====================
    # Ask Superpanda for initial hypotheses
    # ====================

    superpanda_initial_prompt = superpanda_initial_prompt_template.substitute({'belief_graph':json.dumps(belief_graph,indent=2), 'interaction':init_interaction})
    superpanda_dialog = [superpanda_initial_prompt]
#   my_print(superpanda_initial_prompt, 'Superpanda')
    my_print(f"""[ABBREVIATED PROMPT = SPEC + INITIAL SCENARIO + INITIAL BELIEF GRAPH]
Here is the initial scenario:
--------------------
{init_interaction}
--------------------
How do you want to update the belief_graph?""", 'Superpanda', results_dir)
    graph_additions_json, graph_additions_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
    superpanda_dialog.append(graph_additions_txt)
#   my_print(graph_additions_txt, agent_config.SUPERPANDA_LLM)
    my_print("<belief graph updates provided>", agent_config.SUPERPANDA_LLM, results_dir)    

    # ====================
    # Update belief_graph
    # ====================        
    update_belief_graph(belief_graph, graph_additions_json)
#   print_belief_graph(belief_graph, results_dir)			# print it in continue_superpanda4()

    continue_superpanda_interactive()

# ------------------------------

def continue_superpanda_interactive():

    global superpanda_dialog
    global dwlite_dialog
    global belief_graph
    global results_dir

    # still need this for interactive version?
    with open(SUPERPANDA_FOLLOWUP_PROMPT_TEMPLATE_FILE, 'r') as f:
        superpanda_followup_prompt_template = Template(f.read())        

    while True:

        suggested_actions = get_suggested_actions(superpanda_dialog, results_dir)

        # ====================
        # Print the current setup
        # ====================
        print("======================================================================\n"*3)
        print_story_so_far(dwlite_dialog)
        print("----------------------------------------------------------------------")
        print_belief_graph(belief_graph, results_dir)
        print("----------------------------------------------------------------------")        
        print_suggested_actions(suggested_actions)

        # ====================
        # Check if finished
        # ====================
        top_hypotheses = get_top_hypotheses(belief_graph)        
        solution = next((hypothesis for hypothesis in top_hypotheses if is_valid_solution(superpanda_dialog, hypothesis, belief_graph, results_dir)), None)
        if solution:
            print("Found a good solution!!!")
            print("Generating video...")
            make_video(html_and_video_directory=results_dir, video_name="output_video.mp4")
            print("Stopping...")
            break
        
        # ====================
        # Get user input (or automated)
        # ====================
        command = input("What next ('q' to quit)?\n> ")
#       command = "Do the first suggested action"	# Auto mode
        if command.strip().lower() == "q":
            break					# break out of "while True" loop to ipython prompt
        if command.strip().lower() == "":
                pass
        else:
            command_type = classify_command(superpanda_dialog, command)

            if command_type == 'update':
                graph_updates = get_graph_updates(superpanda_dialog, command)
                print("Here's my interpretation of the changes you want to the belief graph:")
                print_suggested_graph_updates(graph_updates, belief_graph)
                confirmation = input("Okay to proceed ('y' or 'n')? ")
                if confirmation.strip().lower() == "y":
                    update_belief_graph(belief_graph, graph_updates)
                    print("Done!")
                else:
                    print("(No changes made)")
                belief_graph_txt = render_hypothesis_tree_with_evidence(belief_graph, as_html=False, html_title="Hypothesis Tree")                
                print("Current Belief Graph:")
                print(belief_graph_txt)
                
            elif command_type == 'do':
                action_txt = get_action_from_command(superpanda_dialog, command)
                response = do_dwlite_action(dwlite_dialog, action_txt)
                interaction_title = call_llm(f"Give a short (2-4 word) title for the following description of an interaction:\n\n{response}\n\nJust return the title, and nothing else.",
                                             model=agent_config.SUPERPANDA_LLM)

                # ====================
                # Add that interaction to the belief graph
                # ====================
    
                id = next_id(belief_graph, "I")		# e.g., -> "I2"
                new_node = {'id':id, 'type':"interaction", 'title':interaction_title, 'description':response}
                belief_graph['nodes'].append(new_node)

    	        # ====================
                # Ask Superpanda for additional hypotheses
                # ====================

                superpanda_followup_prompt = superpanda_followup_prompt_template.substitute({'belief_graph':json.dumps(belief_graph,indent=2), 'interaction':response})
                superpanda_dialog.append(superpanda_followup_prompt)
#               my_print(superpanda_followup_prompt, 'Superpanda')
                my_print(f"""[ABBREVIATED PROMPT = LATEST INTERACTION + UPDATED BELIEF GRAPH]
Here is the result of doing that action:
--------------------
{response}
--------------------
How do you want to update the belief_graph?""", 'Superpanda', results_dir)
                graph_additions_json, graph_additions_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
                superpanda_dialog.append(graph_additions_txt)
#               my_print(graph_additions_txt, agent_config.SUPERPANDA_LLM)
                my_print("<belief graph updates provided>", agent_config.SUPERPANDA_LLM, results_dir)

#               print_suggested_graph_updates(graph_additions_json)	# just suggest them, rather than do them. Record of the suggestions is solely in the conversation history
# No, let's actually do them, it's too painful having user mediate:
                update_belief_graph(belief_graph, graph_additions_json)                

                # print out to trace file / window #2 eventually

            elif command_type == 'think':
                prompt = command
                superpanda_dialog.append(prompt)
                my_print(prompt, 'Superpanda', results_dir)
                answer_txt = call_llm(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
                superpanda_dialog.append(answer_txt)
                my_print(answer_txt, agent_config.SUPERPANDA_LLM, results_dir)

                # after calling GPT, add the response to the dialog (window #3)
                
            else:
                print(f"ERROR! Unrecognized command_type '{command_type}'")

"""
SCREEN LAYOUT [windows]
               
<belief graph> | <rolling log>         <dialog window>
               ----                     What do you want to do next?
               Last interaction         > Suggest possible causes of H2   <- "thinking" act, rather 
            ---- 			 - 
               Suggested graph edits:    - 
               ----                      - 
               Suggested next tasks:    > Show me H1 

Three types of action, each cause updates to a different window:
do <act> - interact with dwlite (window #2)
update <graph> - update the BG (window #1)
think - self-contained GPT call with response in the dialog window (window #3)
"""


# ======================================================================

# return a list of possible actions in the form [{'id':ID, 'title':TITLE, 'action':DESCRIPTION},...,...]}
def get_suggested_actions(superpanda_dialog, results_dir):

    # PEC: 1/13/26 Added explicit prompt about literature search being allowed as an action.
    actions_prompt = """
Now, what are some possible actions you might like to do next, that would best help with your quest?
Possible actions include data analysis actions, experimentation actions, and also literature search actions to uncover other researchers' insights.
Return a list of options, in the following JSON form:

{"possible_actions": [{"id":"A1", "title":TITLE, "action":DESCRIPTION, "rationale":RATIONALE},{"id":"A2",.. },...,...]}
"""
    superpanda_dialog.append(actions_prompt)
    my_print(actions_prompt, 'Superpanda', results_dir)
    actions_json, actions_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
    superpanda_dialog.append(actions_txt)
#   my_print(actions_txt, agent_config.SUPERPANDA_LLM, results_dir)
    my_print("<action list>", agent_config.SUPERPANDA_LLM, results_dir)    

    actions_list = actions_json.get("possible_actions",[])
#   print("actions_list =", actions_list)
    return actions_list

# ======================================================================

def print_story_so_far(dwlite_dialog):
    print("THE STORY SO FAR:")
    for item in dwlite_dialog[1:]:
        print(strip_trailing_question(item))
        print("----------")

# ======================================================================

def print_suggested_actions(suggested_actions, preview_len=80):
    """
    Pretty-print a list of suggested actions.

    Each action is a dict like:
      {'id': ID, 'title': TITLE, 'action': DESCRIPTION}

    Output format:
      ID: TITLE (DESCRIPTION_START...)
    """

    print("SUGGESTED ACTIONS:")
    for a in suggested_actions:
        aid = a.get("id", "")
        title = a.get("title", "")
        desc = a.get("action", "")
        rationale = a.get("rationale", "")        

        if not isinstance(desc, str):
            desc = str(desc)

        desc = " ".join(desc.split())  # normalize whitespace

        if len(desc) > preview_len:
            desc_preview = desc[:preview_len] + "..."
        else:
            desc_preview = desc

        print(f"{aid}: {title} ({desc_preview})\n  - {rationale}\n")

# ======================================================================

def classify_command(superpanda_dialog, command):
    classify_prompt = """
Here are three types of action that the USER can now do:
----------
1. Do an action
do A1                                        # do action A1
interview the colonists                      # do the described action

2. Update the belief graph
add H2 to the graph
add H2
update the confidence in H1 to 70%
Add O3 as evidence for H1, and update the confidence in H1 to 20%
Delete H1

3. Think
What are some common causes of illness?
Why might the colonists be feeling sick?
----------

Here's what the user asked to do:
----------
""" + command + """
----------
Now: classify the action into one of "do", "update", or "think". Return your answer in a simple JSON like this:
{"command_type":TYPE}
where TYPE is one of "do", "update", or "think".
"""
    superpanda_dialog.append(classify_prompt)
    my_print(classify_prompt, 'Superpanda', results_dir)
    classify_json, classify_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
    superpanda_dialog.append(classify_txt)
    my_print(classify_txt, agent_config.SUPERPANDA_LLM, results_dir)

    command_type = classify_json.get("command_type",None)
    return command_type

# ======================================================================

def get_graph_updates(superpanda_dialog, user_graph_updates_txt):
    graph_updates_prompt = """
The user wants to update the belief_graph as follows:
----------
""" + user_graph_updates_txt + """
----------
Please convert these requested updates into the following JSON structure:

{'new_nodes': [{'id':"...", 'type':..., 'title':TITLE, 'description':DESCRIPTION [,'percent_likelihood':<n>]},
               {'id':....,...}, ... ],
 'new_edges': [{'id':"...", 'subject':"...", 'relation':..., 'object':... [, 'percent_strength':<n>]},
               {'id':"...", 'subject':"....., .... }, ...],
 'changed_nodes': [{'id':"...", 'percent_likelihood':<n>},...],       # only need to list the CHANGED fields - all other fields remain unchanged
 'changed_edges': [{'id':"...", 'percent_strength':<n>},...],
 'deleted_nodes': [{'id':"..."}, {'id':"..."}, ...],		      # only need IDs
 'deleted_edges': [{'id':"..."}, {'id':"..."}, ...]
}
"""
    superpanda_dialog.append(graph_updates_prompt)
    my_print(graph_updates_prompt, 'Superpanda', results_dir)
    graph_updates_json, graph_updates_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
    superpanda_dialog.append(graph_updates_txt)
    my_print(graph_updates_txt, agent_config.SUPERPANDA_LLM, results_dir)

    return graph_updates_json

# ======================================================================

def get_action_from_command(superpanda_dialog, command):
    action_prompt = """
The user wants to perform the following action:
----------
""" + command + """
----------
If the action refers to the ID of an earlier suggested action (e.g., "do A1"), substitute
in the action itself (e.g., "go to the kitchen" if A1 is "go to the kitchen"). Otherwise
just repeat the action verbatim. Return your answer in natural language.
"""
    superpanda_dialog.append(action_prompt)
    my_print(action_prompt, 'Superpanda', results_dir)
    action_txt = call_llm(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
    superpanda_dialog.append(action_txt)
    my_print(action_txt, agent_config.SUPERPANDA_LLM, results_dir)

    return action_txt

# ======================================================================

def print_suggested_graph_updates(updates: Dict[str, Any],
                                  belief_graph: Optional[Dict[str, Any]] = None, prefix = "Suggested") -> None:
    """
    Pretty-print belief-graph updates.

    updates format:
      {
        'new_nodes': [...],
        'new_edges': [...],
        'changed_nodes': [...],
        'changed_edges': [...],
        'deleted_nodes': [{'id':...}, ...],
        'deleted_edges': [{'id':...}, ...],
      }

    belief_graph (optional):
      {'nodes': [...], 'edges': [...]}

    If belief_graph is provided, we can:
      - resolve deleted edge IDs to "subject -> object"
      - resolve observation provenance "(from I*)" even if the includes edge wasn't in this update
      - resolve specialization parent for new hypotheses even if specialization edge wasn't in this update
    """

    # --- relations per spec
    REL_INCLUDES = "includes"
    REL_SUPPORTS = "supports"
    REL_CONTRADICTS = "contradicts"
    REL_SPECIALIZATION = "is specialization of"

    # --- helpers
    def pct(v: Any) -> str:
        return f"{int(v)}%" if isinstance(v, (int, float)) else ""

    def short(s: str, n: int = 90) -> str:
        s2 = " ".join(s.split())
        return (s2[: n - 1] + "…") if len(s2) > n else s2

    def node_label(n: Dict[str, Any]) -> str:
        # Prefer title; fall back to shortened description; then id
        t = n.get("title")
        if isinstance(t, str) and t.strip():
            return short(t.strip(), 90)
        d = n.get("description")
        if isinstance(d, str) and d.strip():
            return short(d.strip(), 90)
        return str(n.get("id", ""))

    def node_type_from_id(nid: str) -> str:
        if nid.startswith("H"):
            return "hypothesis"
        if nid.startswith("O"):
            return "observation"
        if nid.startswith("I"):
            return "interaction"
        return ""

    # --- pull update lists
    new_nodes: List[Dict[str, Any]] = list(updates.get("new_nodes") or [])
    new_edges: List[Dict[str, Any]] = list(updates.get("new_edges") or [])
    changed_nodes: List[Dict[str, Any]] = list(updates.get("changed_nodes") or [])
    changed_edges: List[Dict[str, Any]] = list(updates.get("changed_edges") or [])
    deleted_nodes: List[Dict[str, Any]] = list(updates.get("deleted_nodes") or [])
    deleted_edges: List[Dict[str, Any]] = list(updates.get("deleted_edges") or [])

    # --- optional base graph indices
    base_nodes_by_id: Dict[str, Dict[str, Any]] = {}
    base_edges_by_id: Dict[str, Dict[str, Any]] = {}
    if belief_graph:
        base_nodes_by_id = {n.get("id"): n for n in belief_graph.get("nodes", []) if n.get("id")}
        base_edges_by_id = {e.get("id"): e for e in belief_graph.get("edges", []) if e.get("id")}

    # --- new node index (used for titles in this update)
    new_nodes_by_id = {n.get("id"): n for n in new_nodes if n.get("id")}

    # --- Build provenance and specialization maps using BOTH update edges and base edges (if provided)
    obs_from_interactions: defaultdict[str, set[str]] = defaultdict(set)  # O -> {I}
    spec_parent: Dict[str, str] = {}  # H_child -> H_parent

    def ingest_edges(edge_list: List[Dict[str, Any]]) -> None:
        for e in edge_list:
            s = e.get("subject")
            r = (e.get("relation") or "").strip()
            o = e.get("object")
            if not (isinstance(s, str) and isinstance(o, str) and isinstance(r, str)):
                continue

            if r == REL_INCLUDES and s.startswith("I") and o.startswith("O"):
                obs_from_interactions[o].add(s)

            if r == REL_SPECIALIZATION and s.startswith("H") and o.startswith("H"):
                spec_parent[s] = o

    ingest_edges(new_edges)
    if belief_graph:
        ingest_edges(list(belief_graph.get("edges", []) or []))

    # --- Categorize new nodes by type (spec)
    def infer_type(n: Dict[str, Any]) -> str:
        t = n.get("type")
        if isinstance(t, str) and t:
            return t
        nid = n.get("id", "")
        return node_type_from_id(nid) if isinstance(nid, str) else ""

    new_obs = [n for n in new_nodes if infer_type(n) == "observation"]
    new_hyp = [n for n in new_nodes if infer_type(n) == "hypothesis"]
    new_int = [n for n in new_nodes if infer_type(n) == "interaction"]
    new_other = [n for n in new_nodes if n not in new_obs and n not in new_hyp and n not in new_int]

    # --- Sort hypotheses by likelihood desc, then id
    def hyp_sort_key(n: Dict[str, Any]) -> Tuple[float, str]:
        pl = n.get("percent_likelihood")
        return (-(pl if isinstance(pl, (int, float)) else -1.0), str(n.get("id", "")))

    new_hyp.sort(key=hyp_sort_key)
    new_obs.sort(key=lambda n: (-(n.get("percent_likelihood") if isinstance(n.get("percent_likelihood"), (int, float)) else -1.0),
                                str(n.get("id", ""))))
    new_int.sort(key=lambda n: str(n.get("id", "")))

    # --- Edge formatting (spec-aware)
    def edge_strength(e: Dict[str, Any]) -> Optional[float]:
        v = e.get("percent_strength")
        return float(v) if isinstance(v, (int, float)) else None

    def fmt_edge(e: Dict[str, Any]) -> str:
        s = str(e.get("subject", "?"))
        o = str(e.get("object", "?"))
        r = (e.get("relation") or "").strip()

        w = edge_strength(e)
        w_part = f" ({pct(w)})" if w is not None else ""

        if r == REL_SUPPORTS:
            return f"{s} -> {o}{w_part}"
        if r == REL_CONTRADICTS:
            # make the relation explicit so it’s not confused with support
            return f"{s} -> {o} (contradicts {pct(w)})" if w is not None else f"{s} -> {o} (contradicts)"
        if r == REL_INCLUDES:
            return f"{s} includes {o}"
        if r == REL_SPECIALIZATION:
            return f"{s} is specialization of {o}"
        # fallback
        return f"{s} -[{r}]-> {o}{w_part}"

    # Sort edges by strength desc (when present), then subject/object
    def edge_sort_key(e: Dict[str, Any]) -> Tuple[float, str, str, str]:
        w = edge_strength(e)
        # put edges with no strength last (treat as -1)
        ww = w if w is not None else -1.0
        return (-ww, str(e.get("subject", "")), str(e.get("relation", "")), str(e.get("object", "")))

    new_edges_sorted = sorted(new_edges, key=edge_sort_key)

    # --- Node line formatting
    def fmt_observation(n: Dict[str, Any]) -> str:
        nid = str(n.get("id", ""))
        pl = n.get("percent_likelihood")  # not standard in spec for O, but tolerate it
        pl_part = f" {pct(pl)}" if isinstance(pl, (int, float)) else ""
        title = node_label(n)

        from_ids = sorted(obs_from_interactions.get(nid, set()))
        from_part = f" (from {', '.join(from_ids)})" if from_ids else ""

        # Example style: O1 95%: ... (from I2)
        return f"{nid}{pl_part}: {title}{from_part}" if pl_part else f"{nid}: {title}{from_part}"

    def fmt_hypothesis(n: Dict[str, Any]) -> str:
        nid = str(n.get("id", ""))
        title = node_label(n)
        pl = n.get("percent_likelihood")
        pl_part = f" ({pct(pl)})" if isinstance(pl, (int, float)) else ""
        parent = spec_parent.get(nid)
        spec_part = f" (specialization of {parent})" if parent else ""
        return f"{nid}: {title}{pl_part}{spec_part}"

    def fmt_interaction(n: Dict[str, Any]) -> str:
        nid = str(n.get("id", ""))
        title = node_label(n)
        return f"{nid}: {title}"

    # --- Changed nodes/edges (print only fields listed)
    def fmt_changed(d: Dict[str, Any]) -> str:
        _id = d.get("id", "")
        parts = []
        for k, v in d.items():
            if k == "id":
                continue
            parts.append(f"{k}={v}")
        return f"{_id}: " + ", ".join(parts) if parts else str(_id)

    # --- Deletions
    del_node_ids = sorted([d.get("id") for d in deleted_nodes if d.get("id")])

    # For deleted edges, prefer "subject -> object" if resolvable from base graph
    del_edge_items = [d.get("id") for d in deleted_edges if d.get("id")]
    del_edge_pretty: List[str] = []
    for eid in del_edge_items:
        if belief_graph and eid in base_edges_by_id:
            e = base_edges_by_id[eid]
            s = str(e.get("subject", "?"))
            o = str(e.get("object", "?"))
            r = (e.get("relation") or "").strip()
            if r == REL_SUPPORTS:
                del_edge_pretty.append(f"{s} -> {o}")
            elif r == REL_CONTRADICTS:
                del_edge_pretty.append(f"{s} -> {o} (contradicts)")
            elif r == REL_INCLUDES:
                del_edge_pretty.append(f"{s} includes {o}")
            elif r == REL_SPECIALIZATION:
                del_edge_pretty.append(f"{s} is specialization of {o}")
            else:
                del_edge_pretty.append(f"{s} -[{r}]-> {o}")
        else:
            del_edge_pretty.append(str(eid))
    del_edge_pretty = sorted(del_edge_pretty)

    # ---------- Print ----------
    print("----------\n")

    if new_obs:
        print(prefix, "observations:")
        for n in new_obs:
            print(fmt_observation(n))
        print()

    if new_hyp:
        print(prefix, "new Hs:")
        for n in new_hyp:
            print(fmt_hypothesis(n))
        print()

    if new_int:
        print(prefix, "new interactions:")
        for n in new_int:
            print(fmt_interaction(n))
        print()

    if new_other:
        print(prefix, "new nodes:")
        for n in sorted(new_other, key=lambda x: str(x.get("id", ""))):
            nid = str(n.get("id", ""))
            print(f"{nid}: {node_label(n)} ({infer_type(n) or 'node'})")
        print()

    if new_edges_sorted:
        print(prefix, "new edges:")
        for e in new_edges_sorted:
            print(fmt_edge(e))
        print()

    if changed_nodes or changed_edges:
        print(prefix, "changes:")
        if changed_nodes:
            print("Nodes:")
            for d in sorted(changed_nodes, key=lambda x: str(x.get("id", ""))):
                print(f"  {fmt_changed(d)}")
        if changed_edges:
            print("Edges:")
            for d in sorted(changed_edges, key=lambda x: str(x.get("id", ""))):
                print(f"  {fmt_changed(d)}")
        print()

    if del_node_ids or del_edge_pretty:
        print(prefix, "deletions:")
        if del_node_ids:
            print("Nodes: " + ", ".join(del_node_ids))
        if del_edge_pretty:
            print("Edges: " + ", ".join(del_edge_pretty))
        print()

    print("----------")
               
# ======================================================================

# ----------

def is_valid_solution(superpanda_dialog, hypothesis, belief_graph, results_dir):

    id = hypothesis.get("id")
    title = hypothesis.get("title")
    description= hypothesis.get("description")
    likelihood = hypothesis.get("percent_likelihood")
            
    if not hypothesis.get("invalid_solution"):
        if likelihood >= SOLUTION_THRESHOLD:
            print(f"Checking if {id} is valid...")
            prompt = f"""Here is a high-confidence hypothesis:
{id}: {title} - {description}

Question: Does this hypothesis provide a possible solution to the original quest (rather than a different problem or just a subgoal of the original quest)?
Please answer with a JSON:
{{"solves_quest":"yes"}}
or
{{"solves_quest":"no"}}
"""
            superpanda_dialog.append(prompt)
            my_print(prompt, 'Superpanda', results_dir)
            answer_json, answer_txt = call_llm_json(superpanda_dialog, model=agent_config.SUPERPANDA_LLM)
            superpanda_dialog.append(answer_txt)
            my_print(answer_txt, agent_config.SUPERPANDA_LLM, results_dir)

            answer = answer_json["solves_quest"]
            if answer == "yes":
                print("yes!")
                return True
            else:
                print("no.")
                update_belief_graph(belief_graph, {"changed_nodes":[{"id":id,"invalid_solution":True}]})	# cache this is no good
                return False

# ----------

def print_belief_graph(belief_graph, results_dir):
    print("CURRENT BELIEF GRAPH:")
    belief_graph_txt = render_hypothesis_tree_with_evidence(belief_graph, as_html=False, html_title="Hypothesis Tree")
    belief_graph_html = render_hypothesis_tree_with_evidence(belief_graph, as_html=True, html_title="Hypothesis Tree")

    next_html_file = create_next_filename(prefix="hypotheses", ext=".html", dir=results_dir)
    next_svg_file = create_next_filename(prefix="hypotheses", ext=".svg", dir=results_dir)

    my_print(belief_graph_txt, results_dir=results_dir)	# txt to TTY and trace file        
    render_belief_graph(belief_graph, next_svg_file)	# svg to file
    with open(next_html_file, "w", encoding="utf-8") as f:  # tml to file
        f.write(belief_graph_html)

def showme(item_id, belief_graph):
    """
    Pretty-print a node and all relations involving it.
    """
    nodes = {n.get("id"): n for n in belief_graph.get("nodes", [])}
    edges = {n.get("id"): n for n in belief_graph.get("edges", [])}
    
    item = nodes.get(item_id)
    if item is None:
        item = edges.get(item_id)
    if item is None:
        print("ERROR! Can't find item", item_id, "in belief_graph.")
    else:
        jprint(item)

# ------------------------------

def next_id(graph, prefix):
    """
    Generate the next unused ID of the form <prefix><n>,
    where n is the smallest positive integer not yet used.
    """
    used = set()

    for node in graph.get('nodes', []):
        node_id = node.get('id')
        if isinstance(node_id, str) and node_id.startswith(prefix):
            suffix = node_id[len(prefix):]
            if suffix.isdigit():
                used.add(int(suffix))

    n = 1
    while n in used:
        n += 1

    return f"{prefix}{n}"


# ------------------------------

def get_top_hypotheses(belief_graph):
    """
    Returns a list of hypothesis node dicts with the highest percent_likelihood.
    If no hypothesis has a numeric percent_likelihood, returns an empty list.
    """
    hypotheses = [
        node for node in belief_graph.get("nodes", [])
        if node.get("type") == "hypothesis"
        and not node.get("invalid_solution")
        and isinstance(node.get("percent_likelihood"), (int, float))
    ]

    if not hypotheses:
        return []

    max_likelihood = max(node["percent_likelihood"] for node in hypotheses)

    return [
        node for node in hypotheses
        if node["percent_likelihood"] == max_likelihood
    ]

def print_hypotheses(hypotheses):
    for h in hypotheses:
        hid = h.get("id", "<unknown>")
        pct = h.get("percent_likelihood")
        title = h.get("title", "").strip()
        print(f"{hid} ({pct}%): {title}")

# ======================================================================
#		UTILITIES
# ======================================================================

# if results_dir, then print TWICE, once to TTY and once to trace.txt in results_dir
def my_print(text, role=None, results_dir=None):
    if role:
        logger.info(f"================================ {role} =================================")
    logger.info(text)
    if results_dir:
        trace_file = os.path.join(results_dir, "trace.txt")
        with open(trace_file, "a", encoding="utf-8") as f:
            if role:
                f.write(f"================================ {role} =================================\n")
            f.write(text+"\n")
        

# ----------

# returns the path, not just the name
def create_next_dir(prefix="superpanda_results", base_dir="."):
    base_dir = Path(base_dir)
    n = 1
    while True:
        candidate = base_dir / f"{prefix}{n}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        n += 1

# returns the path, not just the name        
def create_next_filename(prefix="hypotheses", ext=".html", dir="."):
    dir = Path(dir)
    n = 1
    while True:
        candidate = dir / f"{prefix}{n}{ext}"
        if not candidate.exists():
            return candidate
        n += 1

# ======================================================================
#		GRAPH RENDERING
# ======================================================================

def render_belief_graph(belief_graph, output_file="belief_graph"):
    """
    Render a belief graph (nodes + edges) to an SVG using Graphviz.

    Parameters
    ----------
    belief_graph : dict
        Dict with keys 'nodes' and 'edges'
    output_file : str
        Output filename without extension (default: 'belief_graph')
    """
    output_file = Path(output_file).with_suffix("")	# strip extension, if any

    dot = Digraph(
        name="BeliefGraph",
        format="svg",
        graph_attr={
            "rankdir": "LR",
            "fontsize": "10",
            "fontname": "Helvetica",
        },
        node_attr={
            "shape": "box",
            "fontname": "Helvetica",
        },
        edge_attr={
            "fontname": "Helvetica",
        },
    )

    # --- Add nodes ---
    for node in belief_graph.get("nodes", []):
        node_id = node["id"]
        node_type = node.get("type", "")
        title = node.get("title", "")
        likelihood = node.get("percent_likelihood")

        label_lines = [f"{node_id}: {title}", f"({node_type})"]
        if likelihood is not None:
            label_lines.append(f"{likelihood}%")

        label = "\n".join(label_lines)

        dot.node(node_id, label=label)

    # --- Add edges ---
    for edge in belief_graph.get("edges", []):
        src = edge["subject"]
        dst = edge["object"]
        relation = edge.get("relation", "")

        strength = edge.get("percent_strength")
        if strength is not None:
            label = f"{relation} ({strength}%)"
        else:
            label = relation

        dot.edge(src, dst, label=label)

    # --- Render ---
    dot.render(str(output_file), cleanup=True)

    return output_file.with_suffix(".svg")		# add suffix back in

# ======================================================================
#	EXPANDED HYPOTHESIS VIEWER
# ======================================================================

from collections import defaultdict
import html

def render_hypothesis_tree_with_evidence(graph, *,
                                        supports_rel=("supports",),
                                        contradicts_rel=("contradicts", "refutes", "challenges", "weakens"),
                                        specialization_rel=("is specialization of", "specialization_of", "specializes"),
                                        includes_rel=("includes", "contains"),
                                        weight_key="percent_strength",
                                        likelihood_key="percent_likelihood",
                                        indent_spaces=4,
                                        max_title_len=80,
                                        as_html=False,
                                        html_title="Graph View"):
    """
    If as_html=False: returns plain text.
    If as_html=True: returns a full HTML page (string) with shaded hypothesis content (not indent).

    Ordering:
      - hypotheses by percent_likelihood desc
      - observations by edge percent_strength desc

    Shading:
      - 100% => bright green
      - 50%  => no shading
      - 0%   => bright red
    """

    nodes = {n["id"]: n for n in graph.get("nodes", [])}

    def node_title(nid):
        t = nodes.get(nid, {}).get("title", "")
        if max_title_len and len(t) > max_title_len:
            t = t[: max_title_len - 1] + "…"
        return t

    def node_type(nid):
        return nodes.get(nid, {}).get("type", "")

    def likelihood(nid):
        v = nodes.get(nid, {}).get(likelihood_key, None)
        return v if isinstance(v, (int, float)) else None

    def is_invalid(hid):
        return bool(nodes.get(hid, {}).get("invalid_solution", False))    

    # --- build edge-derived structures
    children = defaultdict(list)
    parent_of = {}
    incoming_support = defaultdict(list)
    incoming_contra = defaultdict(list)
    obs_from_interactions = defaultdict(list)

    for e in graph.get("edges", []):
        s = e.get("subject")
        r = (e.get("relation") or "").strip()
        o = e.get("object")
        w = e.get(weight_key, None)

        if not s or not r or not o:
            continue

        if r in includes_rel and node_type(s) == "interaction" and node_type(o) == "observation":
            obs_from_interactions[o].append(s)

        if r in specialization_rel and node_type(s) == "hypothesis" and node_type(o) == "hypothesis":
            parent_of[s] = o
            children[o].append(s)

        if node_type(s) == "observation" and node_type(o) == "hypothesis":
            if r in supports_rel:
                incoming_support[o].append((s, w))
            elif r in contradicts_rel:
                incoming_contra[o].append((s, w))

    # roots ordered by likelihood desc
    hypothesis_ids = [nid for nid, n in nodes.items() if n.get("type") == "hypothesis"]
    roots = [h for h in hypothesis_ids if h not in parent_of]
    roots.sort(key=lambda h: (-(likelihood(h) or 0), h))

    # children ordered by likelihood desc within each parent
    for p in children:
        children[p].sort(key=lambda h: (-(likelihood(h) or 0), h))

    def fmt_pct(x):
        return f"{x}%" if isinstance(x, (int, float)) else ""

    def fmt_from(obs):
        srcs = sorted(set(obs_from_interactions.get(obs, [])))
        return f" (from {', '.join(srcs)})" if srcs else ""

    # ---------- output builders ----------
    lines_text = []
    lines_html = []

    def make_indent(level: int) -> str:
        return " " * (indent_spaces * level)

    def clamp01(x):
        return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x

    def bg_for_likelihood(pct):
        """
        Diverging background shading centered at 50%:
          0%   => red, alpha max
          50%  => transparent
          100% => green, alpha max
        """
        if pct is None:
            return None

        pct = max(0.0, min(100.0, float(pct)))
        # Map to [-1, +1] where 0 = 50%
        t = (pct - 50.0) / 50.0  # -1..+1
        a_max = 0.45             # max opacity at extremes
        a = a_max * abs(t)       # 0 at 50%, max at 0/100

        if a < 1e-6:
            return None

        if t > 0:   # green side
            return f"background-color: rgba(0, 200, 0, {a:.3f});"
        else:       # red side
            return f"background-color: rgba(220, 0, 0, {a:.3f});"

    def emit(level, text, *, is_hypothesis=False, h_likelihood=None):
        ind = make_indent(level)
        line = f"{ind}{text}"
        lines_text.append(line)

        if not as_html:
            return

        safe_indent = html.escape(ind)
        safe_text = html.escape(text)

        if is_hypothesis:
            bg = bg_for_likelihood(h_likelihood) or ""
            # NOTE: indent is unshaded; shading starts at first non-space char (the content span)
            lines_html.append(
                f'<div class="line">'
                f'<span class="indent">{safe_indent}</span>'
                f'<span class="hline" style="{bg}">{safe_text}</span>'
                f'</div>'
            )
        else:
            lines_html.append(
                f'<div class="line">'
                f'<span class="indent">{safe_indent}</span>'
                f'<span class="text">{safe_text}</span>'
                f'</div>'
            )

    def walk(hid, level):
        like = likelihood(hid)
        like_str = f" ({like}%)" if like is not None else ""
#       emit(level, f"{hid} {node_title(hid)}{like_str}", is_hypothesis=True, h_likelihood=like)
        label = f"{hid} {node_title(hid)}{like_str}"
        if is_invalid(hid):
            label = f"[{label}]"
        emit(level, label, is_hypothesis=True, h_likelihood=like)

        supp = incoming_support.get(hid, [])
        if supp:
            emit(level + 1, "supported by:")
            for obs, w in sorted(supp, key=lambda t: (-(t[1] or 0), t[0])):
                emit(level + 2, f"{obs} {fmt_pct(w)}: {node_title(obs)}{fmt_from(obs)}")

        contra = incoming_contra.get(hid, [])
        if contra:
            emit(level + 1, "contradicted by:")
            for obs, w in sorted(contra, key=lambda t: (-(t[1] or 0), t[0])):
                emit(level + 2, f"{obs} {fmt_pct(w)}: {node_title(obs)}{fmt_from(obs)}")

        for ch in children.get(hid, []):
            walk(ch, level + 1)

    for r in roots:
        walk(r, 0)
        emit(0, "")  # blank line between trees

    if not as_html:
        return "\n".join(lines_text)

    page = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{html.escape(html_title)}</title>
  <style>
    body {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      margin: 16px;
      background: #ffffff;
      color: #111;
    }}
    .container {{
      max-width: 1100px;
    }}
    .line {{
      white-space: pre;      /* preserve spacing */
      margin: 1px 0;
    }}
    .indent {{
      white-space: pre;
    }}
    .hline {{
      white-space: pre;
      padding: 2px 6px;
      border-radius: 6px;
      border-left: 4px solid rgba(0, 0, 0, 0.12);
    }}
    .text {{
      white-space: pre;
      padding: 2px 6px;
      border-radius: 6px;
    }}
  </style>
</head>
<body>
  <div class="container">
    {''.join(lines_html)}
  </div>
</body>
</html>
"""
    return page

# ======================================================================
#	VERSION 3: LM updates the graph by describing edits
# ======================================================================

from copy import deepcopy

def update_belief_graph(belief_graph, edits, *, in_place=True, prune_dangling_edges=True):
    """
    Apply an edits payload to an existing belief graph.

    belief_graph:
      {"nodes":[{id,...}, ...], "edges":[{id,...}, ...]}

    edits:
      {
        "new_nodes": [...],
        "new_edges": [...],
        "changed_nodes": [{"id": "...", <changed fields>}, ...],
        "changed_edges": [{"id": "...", <changed fields>}, ...],
        "deleted_nodes": [{"id":"..."}, ...],
        "deleted_edges": [{"id":"..."}, ...]
      }

    Behavior:
      - Deletes nodes/edges by id
      - Applies partial updates to nodes/edges (only fields provided)
      - Adds new nodes/edges (id must not already exist)
      - Optionally prunes edges whose subject/object refers to a missing node

    Returns the updated belief graph (same object if in_place=True).
    Raises ValueError on common integrity issues (duplicate ids, missing targets, etc.).
    """
    g = belief_graph if in_place else deepcopy(belief_graph)

    g.setdefault("nodes", [])
    g.setdefault("edges", [])

    # --- Build id->index maps
    def index_by_id(items, kind):
        idx = {}
        for i, item in enumerate(items):
            if "id" not in item:
                raise ValueError(f"{kind} at index {i} is missing an 'id': {item!r}")
            _id = item["id"]
            if _id in idx:
                raise ValueError(f"Duplicate {kind} id {_id!r} in belief_graph.")
            idx[_id] = i
        return idx

    node_idx = index_by_id(g["nodes"], "node")
    edge_idx = index_by_id(g["edges"], "edge")

    def get_list(key):
        v = edits.get(key, [])
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError(f"edits[{key!r}] must be a list, got {type(v).__name__}")
        return v

    # --- 1) Deletions (nodes first, then edges)
    deleted_node_ids = {d["id"] for d in get_list("deleted_nodes")}
    deleted_edge_ids = {d["id"] for d in get_list("deleted_edges")}

    # delete nodes
    if deleted_node_ids:
        # remove by filtering, then rebuild index
        g["nodes"] = [n for n in g["nodes"] if n.get("id") not in deleted_node_ids]
        node_idx = index_by_id(g["nodes"], "node")

    # delete edges explicitly requested
    if deleted_edge_ids:
        g["edges"] = [e for e in g["edges"] if e.get("id") not in deleted_edge_ids]
        edge_idx = index_by_id(g["edges"], "edge")

    # optionally prune edges that now dangle due to node deletion
    if prune_dangling_edges and deleted_node_ids:
        existing_nodes = set(node_idx.keys())
        def edge_ok(e):
            s = e.get("subject")
            o = e.get("object")
            # Only prune if it looks like a node reference and is missing
            if s in existing_nodes and o in existing_nodes:
                return True
            # If subject/object are missing or not node ids, keep conservative? Here we prune only when missing.
            return (s in existing_nodes) and (o in existing_nodes)

        # The above is strict; better: prune when subject/object refers to a missing node id
        def edge_ok(e):
            s = e.get("subject")
            o = e.get("object")
            if s in existing_nodes and o in existing_nodes:
                return True
            # if either is a string and not present, prune
            if isinstance(s, str) and s not in existing_nodes:
                return False
            if isinstance(o, str) and o not in existing_nodes:
                return False
            return True

        g["edges"] = [e for e in g["edges"] if edge_ok(e)]
        edge_idx = index_by_id(g["edges"], "edge")

    # --- 2) Changes (partial updates)
    for patch in get_list("changed_nodes"):
        nid = patch.get("id")
        if not nid:
            raise ValueError(f"changed_nodes entry missing id: {patch!r}")
        if nid not in node_idx:
            raise ValueError(f"changed_nodes refers to unknown node id {nid!r}")
        target = g["nodes"][node_idx[nid]]
        for k, v in patch.items():
            if k == "id":
                continue
            target[k] = v

    for patch in get_list("changed_edges"):
        eid = patch.get("id")
        if not eid:
            print(f"WARNING: changed_edges entry missing id: {patch!r}")
        elif eid not in edge_idx:
            print(f"WARNING: changed_edges refers to unknown edge id {eid!r}")
        else:
            target = g["edges"][edge_idx[eid]]
            for k, v in patch.items():
                if k == "id":
                    continue
                target[k] = v

    # --- 3) Additions (new nodes, then new edges)
    for n in get_list("new_nodes"):
        nid = n.get("id")
        if not nid:
            raise ValueError(f"new_nodes entry missing id: {n!r}")
        if nid in node_idx:
            raise ValueError(f"new_nodes tries to add existing node id {nid!r}")
        g["nodes"].append(n)
        node_idx[nid] = len(g["nodes"]) - 1

    existing_nodes = set(node_idx.keys())
    for e in get_list("new_edges"):
        eid = e.get("id")
        if not eid:
            raise ValueError(f"new_edges entry missing id: {e!r}")
        if eid in edge_idx:
            raise ValueError(f"new_edges tries to add existing edge id {eid!r}")

        # basic referential checks (optional but usually helpful)
        s = e.get("subject")
        o = e.get("object")
        if isinstance(s, str) and s not in existing_nodes:
            raise ValueError(f"new_edges edge {eid!r} has unknown subject node id {s!r}")
        if isinstance(o, str) and o not in existing_nodes:
            raise ValueError(f"new_edges edge {eid!r} has unknown object node id {o!r}")

        g["edges"].append(e)
        edge_idx[eid] = len(g["edges"]) - 1

    return g

# ======================================================================
#		AUTO CREATE A NEW MURDER-MYSTERY SCENARIO
# ======================================================================

def generate_murder_mystery():
    print("Generating new murder mystery...", end="")
    prompt = """
I'm using a language model to act as game-master for a murder-mystery text-adventure game with a human user.
Each murder-mystery "quest" is defined by:
  scenario_for_user: A description of the murder mystery that the game master presents to the user to solve
  scenario_for_system = A description of the same murder mystery that describes the correct solution, as well as additional background knowledge
     to help the game-master know how to respond to the user's actions.
These two items are both strings, and stored together in the data structure:
    {"scenario_for_user": <scenario_for_user>,
     "scenario_for_system": <scenario_for_system>}

Here is an example:
{
  "scenario_for_user": "You arrive at Blackthorne Manor, an isolated Victorian estate on the edge of the moors, just after dawn.\nThe night before, during a small dinner gathering, Edmund Blackthorne, the wealthy and reclusive owner of the manor, was found dead in his locked study.\n\nThe official cause of death is unclear. There are no obvious signs of forced entry, no weapon found at the scene, and every guest insists they were elsewhere when the death occurred.\n\nA storm knocked out power overnight. Phone lines were down. No one could leave.\n\nYou must investigate the manor, question the guests, and piece together the truth before the authorities arrive at sunset.\n\nYour goal: Identify who killed Edmund Blackthorne, how they did it, and why.\n\nAfter initial interviews, you make a note of the following cast of victim and suspects:\n\nVictim: Edmund Blackthorne (62)\nIndustrialist, collector, secretive. Known for cutting people out of his will without warning.\n\nSuspects\nClara Blackthorne (58) – Wife:\n - Calm, distant, emotionally cold\n - Slept in a separate bedroom\n - Claims Edmund was planning a reconciliation\nJulian Blackthorne (34) – Nephew\n - Financially struggling\n - Recently asked Edmund for money\n - Claims he retired early to the guest wing\nMargaret Hale (45) – Personal secretary\n - Worked for Edmund for 15 years\n - Had access to documents and schedules\n - Claims she left before dinner ended\nDr. Leonard Price (50) – Family physician\n - Treated Edmund for heart problems\n - Present due to \"medical concerns\"\n - Claims he was preparing medication all evening\nEvelyn Moore (28) – Housekeeper\n - Recently hired\n - Knows the layout of the house\n - Claims she never entered the study\n\nYour initial observations of the crime scene are as follows:\n - Edmund found slumped in his chair, desk lamp still on\n - Door locked from the inside\n - Half-finished glass of brandy\n - Fireplace ashes still warm\n - No visible wounds\n - A faint smell of bitter almonds (subtle, easily missed)",
  "scenario_for_system": "Murderer: Clara Blackthorne (wife)\n\nMethod:\n\nCyanide poison concealed in a dissolvable capsule\n\nHidden in Edmund’s vitamin supplement\n\nEdmund added the supplement to his brandy himself\n\nPoison took effect ~15–20 minutes later\n\nLocked Room Explanation:\n\nEdmund locked the study door himself (habit)\n\nNo one entered afterward\n\nPoison acted after isolation\n\nMotive:\n\nEdmund secretly changed his will that afternoon\n\nClara was completely cut out\n\nShe discovered a draft earlier that day\n\nMurder preserves her access to the estate until probate\n\nKey Consistency Constraints:\n\nCyanide smell fades quickly\n\nNo physical struggle\n\nNo residue left behind\n\nClara had intimate routine access\n\nRED HERRINGS (GM GUIDANCE)\n\nUse these to mislead without contradiction:\n\nRed Herring 1 — Julian (Nephew)\n\nFinancial desperation\n\nArgument with Edmund\n\nMuddy shoes from the moor\n\n- Timeline disproves opportunity\n\nRed Herring 2 — Dr. Price\n\nAccess to drugs\n\nMedical bag\n\nDisagreed with Edmund’s drinking\n\n- All medications accounted for\n\nRed Herring 3 — Fireplace\n\nBurned papers\n\nSuggests destroyed evidence\n\n- Old personal letters only\n\nRed Herring 4 — Evelyn (Housekeeper)\n\nNervous behavior\n\nKnows hidden passages\n\n- Hiding unrelated personal issue\n\nINTERACTION STYLE\n\nUse second-person narration (\"You enter the study...\")\nAllow:\n\nFree exploration\n\nObject inspection\n\nDialogue and re-questioning\n\nConfrontation with evidence\n\nNPCs adapt behavior as suspicion increases\n\nClara remains composed longer than others"
}

Now: Please generate a NEW murder mystery in the same JSON format. Make it challenging.
"""
    new_quest_json, new_quest_txt = call_llm_json(prompt, model=agent_config.SUPERPANDA_LLM)
    print("done!")
    return new_quest_json
    
