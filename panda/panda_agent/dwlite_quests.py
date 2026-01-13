
'''
FORMAT:
dwlite_quests[6] = \
    {'scenario_for_user':"""...""",
     'scenario_for_system':"""..."""}
'''

# ======================================================================
#			QUESTS
# ======================================================================

dwlite_quests = {}

# ========================================
# space sickness 0: A subset of the local food has become **contaminated with mold**.  (no distractors)
# ========================================

dwlite_quests[0] = \
    {'scenario_for_user':"""
You are in the common area of the habitation module on Planet X. A colonist has just complained of feeling queasy after eating some local food, and the mission commander has asked you to investigate what's going on and prevent future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with instruments, medical bay, and other colonists who can be interviewed.
""",

     'scenario_for_system':"""
### **2. Current Quest: Space Illness (Space Sick Theme)**

The current task is the **Space Illness** challenge.

High-level premise for the player:

* Some colonists occasionally feel mildly ill (e.g., nausea, stomach upset, headache) after eating local food from Planet X.

* The player's goal is to determine **what is causing the illness** and **implement a fix** so that future colonists no longer get sick from this cause.

Hidden ground truth (for you, the simulator):

* A subset of the local food has become **contaminated with mold**.

* Mold contamination can:

  * Be seen directly with certain instruments (e.g., microscope, mold-stain test, special culture plate).

  * Be detected indirectly via abnormal readings from other instruments (e.g., a spectrometer showing anomalous peaks).

  * Be inferred behaviorally (e.g., contaminated food becomes safe once thoroughly cooked, while uncooked portions still cause illness).

* Do not introduce any **distractor signals** that indicate another cause - keep it simple for now.
"""}

# ========================================
# space sickness 1: A subset of the local food has become **contaminated with mold**.  (WITH distractors)
# ========================================

dwlite_quests[1] = \
    {'scenario_for_user':"""
You are in the common area of the habitation module on Planet X. A colonist has just complained of feeling queasy after eating some local food, and the mission commander has asked you to investigate what's going on and prevent future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with instruments, medical bay, and other colonists who can be interviewed.
""",
     'scenario_for_system':"""
### **2. Current Quest: Space Illness (Space Sick Theme)**

The current task is the **Space Illness** challenge.

High-level premise for the player:

* Some colonists occasionally feel mildly ill (e.g., nausea, stomach upset, headache) after eating local food from Planet X.

* The player's goal is to determine **what is causing the illness** and **implement a fix** so that future colonists no longer get sick from this cause.

Hidden ground truth (for you, the simulator):

* A subset of the local food has become **contaminated with mold**.

* Mold contamination can:

  * Be seen directly with certain instruments (e.g., microscope, mold-stain test, special culture plate).

  * Be detected indirectly via abnormal readings from other instruments (e.g., a spectrometer showing anomalous peaks).

  * Be inferred behaviorally (e.g., contaminated food becomes safe once thoroughly cooked, while uncooked portions still cause illness).

* Introduce a few **distractor signals** that are *not* the true cause (for example, some foods might be slightly radioactive or have other unusual properties that look suspicious but are ultimately irrelevant to the illness). However, don't make them so realistic that they could plausibly be the cause. If the agent pursues them, eventually provide evidence that shows the distractors are false.
"""}

# ========================================
# space sickness 2: A subset of the local food has become **contaminated with mold**.  (more extensive distractors)
# ========================================

dwlite_quests[2] = \
    {'scenario_for_user':"""
You are in the common area of the habitation module on Planet X. A colonist has just complained of feeling queasy after eating some locally grown food. A few others mention mild symptoms as well, though not everyone who ate the same meal feels sick.

There have been recent discussions among the crew about unfamiliar environmental factors on Planet X - including trace radiation in the soil, unusual atmospheric compounds, and the challenges of preparing alien crops safely. One cook mentions they were rushed during meal prep, while a botanist notes that some native plants contain compounds that behave differently when cooked.

The mission commander has asked you to investigate what's going on and prevent future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with instruments, medical bay, and other colonists who can be interviewed.
""",
     'scenario_for_system':"""
### **2. Current Quest: Space Illness (Space Sick Theme)**

The current task is the **Space Illness** challenge.

High-level premise for the player:

* Some colonists occasionally feel mildly ill (e.g., nausea, stomach upset, headache) after eating local food from Planet X.

* The player's goal is to determine **what is causing the illness** and **implement a fix** so that future colonists no longer get sick from this cause.

Hidden ground truth (for you, the simulator):

* A subset of the local food has become **contaminated with mold**.

* Mold contamination can:

  * Be seen directly with certain instruments (e.g., microscope, mold-stain test, special culture plate).

  * Be detected indirectly via abnormal readings from other instruments (e.g., a spectrometer showing anomalous peaks).

  * Be inferred behaviorally (e.g., contaminated food becomes safe once thoroughly cooked, while uncooked portions still cause illness).

* Introduce the following **distractor signals** that are *not* the true cause:

  *  some foods might be slightly radioactive, but that is ultimately irrelevant to the illness

  * [something else] 

  However, don't make them so realistic that they could plausibly be the cause. If the agent pursues them, eventually provide evidence that shows the distractors are false.
"""}

# ========================================
# space sickness 3: A subset of the local food has become **contaminated with mold**.  (more extensive distractors)
# ========================================

dwlite_quests[3] = \
    {
        'scenario_for_user':"""
You are in the habitation module on Planet X. Over the past two weeks, several colonists have reported intermittent nausea, headaches, or stomach discomfort. The symptoms are mild but persistent, and not everyone is affected in the same way.

The illnesses seem loosely associated with meals, but no single dish or ingredient has been conclusively identified. Some colonists report feeling fine one day and unwell the next, even after eating similar foods. Others suspect stress, environmental exposure, or unfamiliar local biology may be playing a role.

The mission commander is concerned that the problem may worsen over time or affect critical personnel. You are asked to investigate the situation, identify the underlying cause or causes, and implement a solution that prevents future cases. You have access to the habitation module, kitchen, hydroponics bay, science lab with analytical instruments, medical bay, environmental sensors, and colonists who can be interviewed.
""",

        'scenario_for_system':"""
### **Current Quest: Space Illness (Extended / Hard Mode)**

This is a **multi-causal investigation challenge** designed to require iterative hypothesis testing and evidence integration.

---

## Ground Truth (Hidden from Player)

The true underlying cause is **intermittent mold contamination** affecting a subset of locally grown food, with the following properties:

* Mold growth depends on **storage conditions**, not just the food source.
* Mold spores survive on some foods unless they are **thoroughly cooked**.
* Low-level exposure causes **delayed, variable symptoms**, not immediate illness.
* Mold presence fluctuates over time, leading to inconsistent observations.

There is **no single "smoking gun" observation** early in the investigation.

---

## Complicating Factors (Deliberate)

The following factors are *real*, *detectable*, and *partially correlated* with illness — but are **not sufficient causes on their own**:

### 1. Environmental Radiation (True but Irrelevant)
* Certain crops absorb trace radiation from Planet X soil.
* Instruments may detect slightly elevated radiation in some foods.
* Radiation levels are **below known thresholds** for acute illness.
* Radiation correlates with **where food is grown**, not when illness occurs.

### 2. Food Preparation Effects (Partially True)
* Cooking food thoroughly reduces symptoms.
* However:
  * This is **not** because toxins or radiation are neutralized.
  * Cooking works because it **kills mold**, which should not be obvious initially.

### 3. Mild Nutritional Stress (Background Noise)
* Colonists show minor electrolyte imbalances and fatigue.
* These amplify symptoms but **do not cause illness independently**.
* Supplements improve wellbeing but **do not prevent recurrence**.

### 4. Sensor and Data Ambiguity
* Some analytical instruments occasionally produce ambiguous or noisy readings.
* Early lab tests may return:
  * "Inconclusive"
  * "Within expected variance"
  * "Anomalous but not diagnostic"

The simulator should **avoid early definitive results** unless the player designs targeted tests.

---

## Simulator Behavior Guidelines (Critical)

The simulator LLM must follow these rules:

### A. Slow Down Convergence
* Do NOT confirm or deny hypotheses based on a single action.
* Require **at least 2–3 converging lines of evidence** before allowing strong conclusions.
* Early observations should support **multiple competing hypotheses**.

### B. Reward Experimental Design
* Passive observation and interviews alone should be insufficient.
* Strong evidence requires:
  * Controlled comparisons (e.g., cooked vs uncooked food)
  * Time-based reasoning (e.g., symptom delay)
  * Environmental manipulation (e.g., changing storage conditions)

### C. Penalize Premature Fixes
* If the player implements an incorrect or incomplete fix:
  * Symptoms may decrease temporarily
  * New cases should still appear later
* Only a fix that addresses **mold growth and storage** fully resolves the problem.

### D. Encourage Hypothesis Revision
* When evidence contradicts an active hypothesis:
  * Surface the contradiction clearly
  * Do NOT automatically suggest the correct alternative
* Allow the player to persist in false beliefs if they ignore evidence.

### E. Behavioral Evidence Matters
* Colonist reports may be:
  * Incomplete
  * Biased
  * Inconsistent
* Objective tests should sometimes contradict testimony.

---

## End-State Resolution Criteria

The quest is considered successfully solved ONLY when the player:

1. Identifies mold contamination as the primary cause
2. Explains why:
   * Symptoms are intermittent
   * Cooking helps but does not fully explain the issue
   * Radiation and nutrition are red herrings
3. Implements a **robust prevention strategy**, such as:
   * Improved food storage protocols
   * Regular mold screening
   * Changes to harvesting or preparation workflow
4. Verifies success by:
   * Demonstrating symptom elimination over time
   * Showing negative mold tests on future food batches

If the player only identifies mold without implementing prevention, the quest should **not** fully resolve.

---

## Failure Modes to Support

The simulator should explicitly allow the following incorrect outcomes:

* Blaming radiation → unnecessary mitigation, illness persists
* Blaming stress → symptoms continue
* Over-cooking all food → partial success, morale drops, some illness remains
* Nutritional supplements only → no real improvement

These outcomes should feel *plausible but unsatisfying*.

---

## Tone and Style

* Maintain scientific neutrality.
* Avoid overt hints toward mold unless earned.
* Prefer phrases like:
  * "The results are suggestive but not definitive."
  * "This observation could be consistent with several explanations."
  * "Further testing under controlled conditions may be informative."

The goal is to require **iterative reasoning, hypothesis management, and causal modeling**, not a linear checklist.
"""
    }
    
# ========================================
# Proteomics
# ========================================

dwlite_quests[4] = \
    {'scenario_for_user':"""You have arrived at a remote research preserve on Planet X that hosts several closely related animal species. Most of these species are believed to have evolved locally, but biologists suspect that **one species may have migrated here from an isolated island long ago**, making it biologically distinct.

Your task is to determine which species is the outlier. You have access to a **portable protein meter** that can measure the relative abundance of specific proteins in individual animals. Protein concentrations are reported as values between 0 and 1.

The animals roam freely across the preserve, and you may need to locate, track, and measure multiple individuals from each species. The environment includes a field station with basic visualization tools, note-taking equipment, and the ability to revisit animals for repeat measurements.

The mission lead emphasizes that no single protein is expected to be decisive on its own. You will likely need to collect multiple measurements and reason about patterns across species to identify the one that does not belong.""",
    "system":"""
### **Current Quest: Proteomic Outlier Detection (Challenge Difficulty)**

This is a **high-dimensional clustering and outlier-identification challenge**.

---

## Ground Truth (Hidden from Player)

* There are **N animal species** in the habitat (suggested: 5 to 7 species), each with multiple individuals.
* Exactly **one species** is an evolutionary outlier, having migrated from an isolated island in the distant past.
* Each individual animal has three measurable protein concentrations:
  * Protein A
  * Protein B
  * Protein C
* All protein concentration values are real numbers in the range **[0, 1]**.

### Data Generation Model (Hidden)

* All animals' protein vectors lie on the **surface of a sphere in 3D protein space**.
* The sphere is defined by:
  * A randomly chosen center point \\( c = (c_A, c_B, c_C) \\), with each component in [0.2, 0.8].
* **Inlier species**:
  * Individuals lie on a sphere of radius approximately **0.1** from the center.
  * Small noise may be added, but distances from the center remain tightly clustered.
* **Outlier species**:
  * Individuals lie on a sphere of radius approximately **0.4** from the same center.
  * Distances are consistently much larger than those of inliers.

Visually (to the simulator), inliers and outliers are clearly separable in 3D protein space.

---

## Player-Facing Constraints and Ambiguity

* The player is **never shown the center point or distances directly**.
* The player only observes raw protein readings per animal.
* No individual protein dimension alone is sufficient to identify the outlier.
* Pairwise (2D) projections may appear partially overlapping, requiring true 3D reasoning.

---

## Simulator Behavior Guidelines

### A. Measurement Mechanics

* Each protein-meter measurement returns a triple:
  * (Protein A, Protein B, Protein C)
* Measurements are deterministic but may include **minor measurement noise** (±0.01).
* Repeat measurements on the same animal return consistent values within noise bounds.

### B. Species-Level Reasoning

* Individual animals may vary slightly, but **species-level structure must be clear** when enough samples are collected.
* The simulator must NOT explicitly label species as inliers or outliers.
* If the player samples too few individuals, clustering should appear ambiguous.

### C. Encourage Proper Analysis

* The simulator should support (implicitly or explicitly):
  * Aggregating measurements
  * Computing distances or similarities
  * Visualizing data (e.g., scatter plots, if the player requests them)
* If the player requests only summary statistics (e.g., means per protein), those alone should be **insufficient** to solve the task reliably.

### D. Discourage Shortcuts

* Do NOT allow success from:
  * A single measurement
  * One-dimensional thresholding
  * Narrative explanations without data analysis

* If the player guesses without adequate evidence, respond with uncertainty and request justification.

---

## Success Criteria

The quest is considered solved ONLY if the player:

1. Correctly identifies the outlier species
2. Provides a justification based on **multi-sample, three-dimensional protein analysis**
3. Explains why this species is distinct relative to the others (e.g., consistently farther from a shared cluster center)

---

## Failure Modes to Allow

The simulator should permit and respond plausibly to the following incorrect approaches:

* Focusing on only one or two proteins
* Using averages that mask geometric structure
* Misidentifying a noisy inlier as the outlier due to insufficient sampling

In these cases, provide feedback such as:
* "The evidence appears inconclusive."
* "Several species still appear compatible with your hypothesis."

---

## Tone and Style

* Scientific and observational
* Avoid explicit references to spheres, radii, or outliers unless inferred by the player
* Prefer language like:
  * "These samples appear tightly grouped."
  * "This species shows a consistent deviation across multiple dimensions."

The goal of this challenge is to test **high-dimensional reasoning, clustering intuition, and careful experimental design**, not rote calculation.
     """}

# ========================================
# Chemistry
# ========================================

dwlite_quests[5] = \
    {'scenario_for_user':"""You have been assigned to a materials science lab on Planet X, where corrosion has become a growing problem for exposed equipment. One critical component—a heavily rusted mechanical coupling—must be restored before it can be reused.

You have access to a set of **chemical dispensers**, each containing a different reactive compound. By combining these chemicals in chosen proportions, you can prepare experimental solutions and immerse the rusted object to observe the effect. After each treatment, the object’s condition can be visually inspected and classified as still heavily rusted, moderately rusted, or lightly rusted.

The chief engineer warns that the solution space is large: there is no obvious recipe, no single chemical is sufficient on its own, and small changes in concentration may matter. You are asked to systematically explore the space of possible mixtures, learn from partial successes, and ultimately determine a formulation that reliably removes rust.

You may prepare and test as many solutions as you like, but each test takes time and resources, so efficiency matters.""",
     "system": """### **Current Quest: Rust Removal via Chemical Optimization (Challenge Difficulty)**

This quest evaluates the agent’s ability to **search a large combinatorial space using graded feedback (hill-climbing)** rather than brute force or guessing.

---

## Ground Truth (Hidden from Player)

* There are **four chemical dispensers**, labeled:
  * Chemical A
  * Chemical B
  * Chemical C
  * Chemical D

* A solution is defined by a **4-dimensional concentration vector**:
  * (a, b, c, d)
  * Each component is a non-negative integer representing "parts" of that chemical.
* At least **two chemicals must be present** in the correct solution.
* The correct solution has a **specific ratio** of chemicals (e.g., 1:2:1:0), unknown to the player.

The true rust-removal effectiveness depends on the **cosine similarity** between the player’s tested solution vector and the hidden correct vector.

---

## Rust Response Model (Hidden)

When the rusted object is immersed in a solution:

* Compute cosine similarity between:
  * Player’s solution vector
  * Correct solution vector

* Map similarity to observable outcomes:
  * Low similarity → object remains **heavily rusted**
  * Medium similarity → object becomes **moderately rusted**
  * High similarity → object becomes **lightly rusted**

This produces a **smooth hill-climbing signal**: solutions closer in direction (ratio) to the target perform better, even if not exact.

Absolute scale (total parts) should not matter as much as **relative proportions**.

---

## Simulator Behavior Guidelines

### A. Exploration Over Enumeration

* The simulator must NOT reveal the full solution space or the correct recipe.
* Early attempts should almost always result in partial or no improvement.
* Slight improvements between attempts should be noticeable if the agent moves closer in chemical ratio.

### B. Graded, Noisy Feedback

* Feedback should be **qualitative**, not numeric.
* Use descriptions such as:
  * "Some surface rust has loosened, but large patches remain."
  * "The metal looks cleaner, though discoloration is still visible."
* Do NOT explicitly mention similarity scores, vectors, or cosine similarity.

### C. Discourage Naive Strategies

The simulator should ensure that the following strategies are insufficient:

* Trying each chemical alone
* Adding more of every chemical equally
* Random guessing without iteration

If the agent does this, provide feedback that does not meaningfully improve.

### D. Support Hill-Climbing Behavior

* If the agent:
  * Adjusts ratios incrementally
  * Compares outcomes across trials
  * Infers which chemicals contribute positively or negatively

Then the simulator should provide **monotonic improvements** when appropriate.

Small ratio changes should sometimes improve and sometimes worsen results, encouraging careful tracking.

### E. Allow Plateaus and Local Optima

* Some combinations should appear to work "reasonably well" but are still suboptimal.
* The agent must refine ratios further to reach the best outcome.

---

## Success Criteria

The quest is considered solved ONLY if the agent:

1. Identifies a chemical mixture whose effect consistently produces a **lightly rusted** outcome
2. Demonstrates that this outcome is reproducible
3. Provides a rationale for why this mixture is superior to nearby alternatives (e.g., ratio sensitivity)

Exact numerical ratios do not need to be stated verbatim, but the mixture used must be directionally equivalent to the hidden correct solution.

---

## Failure Modes to Support

The simulator should allow the following incorrect but plausible outcomes:

* Overfitting to a mediocre solution that only partially removes rust
* Misattributing improvement to total concentration instead of ratio
* Abandoning exploration too early after modest success

In such cases, respond with observations like:
* "While improved, the rust removal is incomplete."
* "Further refinement may be possible."

---

## Tone and Style

* Experimental and procedural
* Avoid instructional hints about optimization algorithms
* Emphasize empirical iteration and comparison

The goal of this challenge is to test the agent’s ability to **navigate a large solution space using incremental feedback**, mirroring real-world experimental chemistry."""
}

# ========================================
# 6. Alzheimer's
# ========================================

dwlite_quests[6] = \
    {'scenario_for_user':"""You are performing Alzheimer's research in the lab on Planet X, looking at the SEA-AD dataset, and you are wrestling with a puzzle: Two individuals with similar continuous pseudo-progression scores (CPS) show nearly identical global amyloid and tau burden; Yet a specific population of visual cortex neurons behaves very differently between them. In one brain, the V1-specific L4 IT neuron subtypes show steep loss; in the other, those same cells appear relatively preserved. Your quest is to perform research to answer the question:
	"Why are these specialized L4 neurons selectively vulnerable in one case but resilient in another, given comparable disease stage?"
""",

     'scenario_for_system':"""### **Current Quest: Selective Neuronal Vulnerability in Alzheimer's Disease (Challenge Difficulty)**

This quest evaluates the agent’s ability to reason about **cell-type–specific vulnerability** in Alzheimer’s disease by integrating multi-level evidence (cellular, circuit, and molecular) rather than relying on global pathology measures.

---

## Ground Truth (Gold Answer – Hidden from Player)

**Correct explanation:**

The differential vulnerability of V1 L4 IT neuron subtypes arises from **differences in network context and trans-synaptic tau exposure**, rather than differences in global amyloid or tau burden.

Specifically:
* Although overall amyloid and tau levels are similar, the vulnerable individual shows **greater upstream tau pathology and synaptic tau seeding activity** in association cortices that project into V1.
* This leads to **earlier and more intense trans-synaptic tau propagation** into V1 L4 IT neurons in that brain.
* In the resilient individual, V1 occupies a more terminal or weakly connected position relative to tau-propagating networks, resulting in delayed exposure despite similar CPS.

Thus, **network topology and synaptic connectivity**, not global disease stage, explain the selective loss versus preservation of these neurons.

---

## Plausible but Incorrect Explanations (Red Herrings)

The simulator should actively support investigation of the following hypotheses, while ensuring they ultimately fail to fully explain the observations:

### Distractor 1: Global Tau Toxicity Thresholds
* Hypothesis: Small, unmeasured differences in total tau burden crossed a toxicity threshold in one individual.
* Why it seems plausible:
  * Tau is a known driver of neurodegeneration.
* Why it is incorrect:
  * More sensitive analyses still show comparable tau burden.
  * Does not explain **cell-type specificity** within the same region.

### Distractor 2: Intrinsic Molecular Resilience of L4 IT Neurons
* Hypothesis: The preserved neurons express protective genes (e.g., chaperones, anti-apoptotic factors).
* Why it seems plausible:
  * Differential gene expression is commonly invoked.
* Why it is insufficient:
  * Expression differences are modest and inconsistent.
  * Similar molecular profiles exist in both brains prior to degeneration.

### Distractor 3: Technical or Sampling Artifacts
* Hypothesis: Differences arise from sampling bias, batch effects, or cell annotation errors.
* Why it seems plausible:
  * Single-cell and single-nucleus data are noisy.
* Why it is ruled out:
  * Independent validation (e.g., histology, multiple sections) confirms the pattern.

---

## Simulator Behavior Guidelines

### A. Evidence Gradualism
* Do NOT reveal the gold explanation directly.
* Early analyses should support **multiple competing hypotheses**.
* Allow partial evidence for intrinsic or molecular explanations that later prove insufficient.

### B. Multi-Modal Reasoning Required

The agent should need to integrate:
* Cell-type–specific abundance changes
* Regional and circuit-level tau pathology
* Synaptic or propagation-based interpretations

No single analysis (e.g., differential expression alone) should fully resolve the question.

### C. Encourage Comparative Reasoning
* The simulator should emphasize **why two similar CPS cases diverge** rather than focusing on absolute severity.
* Prompt the agent (implicitly) to ask:
  * Where did tau likely come from?
  * Which regions project into V1?
  * What differs between the two brains upstream of V1?

### D. Penalize Oversimplified Explanations

If the agent concludes:
* "More amyloid"
* "More tau overall"
* "Random variability"

Respond with contradictions or missing-evidence prompts, such as:
* "This does not explain why other V1 neurons are spared."
* "The global pathology measures remain matched."

---

## Tone and Style

* Scientific, hypothesis-driven
* Only present the (simulated) experimental results. Do NOT present the interpretation of them (e.g., "the results seem inconclusive"). The interpretation is for the user to make, not for the simulator to provide.

The goal of this challenge is to test **causal reasoning in systems neuroscience**, not recall of Alzheimer's facts.
"""}

# ======================================================================
#		MURDER MYSTERY
# ======================================================================

dwlite_quests[7] = \
    {'scenario_for_user':"""
You arrive at Blackthorne Manor, an isolated Victorian estate on the edge of the moors, just after dawn.
The night before, during a small dinner gathering, Edmund Blackthorne, the wealthy and reclusive owner of the manor, was found dead in his locked study.

The official cause of death is unclear. There are no obvious signs of forced entry, no weapon found at the scene, and every guest insists they were elsewhere when the death occurred.

A storm knocked out power overnight. Phone lines were down. No one could leave.

You must investigate the manor, question the guests, and piece together the truth before the authorities arrive at sunset.

Your goal: Identify who killed Edmund Blackthorne, how they did it, and why.

After initial interviews, you make a note of the following cast of victim and suspects:

Victim: Edmund Blackthorne (62)
Industrialist, collector, secretive. Known for cutting people out of his will without warning.

Suspects
Clara Blackthorne (58) – Wife: 
 - Calm, distant, emotionally cold
 - Slept in a separate bedroom
 - Claims Edmund was planning a reconciliation
Julian Blackthorne (34) – Nephew
 - Financially struggling
 - Recently asked Edmund for money
 - Claims he retired early to the guest wing
Margaret Hale (45) – Personal secretary
 - Worked for Edmund for 15 years
 - Had access to documents and schedules
 - Claims she left before dinner ended
Dr. Leonard Price (50) – Family physician
 - Treated Edmund for heart problems
 - Present due to "medical concerns"
 - Claims he was preparing medication all evening
Evelyn Moore (28) – Housekeeper
 - Recently hired
 - Knows the layout of the house
 - Claims she never entered the study

Your initial observations of the crime scene are as follows:
 - Edmund found slumped in his chair, desk lamp still on
 - Door locked from the inside
 - Half-finished glass of brandy
 - Fireplace ashes still warm
 - No visible wounds
 - A faint smell of bitter almonds (subtle, easily missed)
""",
     'scenario_for_system':"""
Murderer: Clara Blackthorne (wife)

Method:

Cyanide poison concealed in a dissolvable capsule

Hidden in Edmund’s vitamin supplement

Edmund added the supplement to his brandy himself

Poison took effect ~15–20 minutes later

Locked Room Explanation:

Edmund locked the study door himself (habit)

No one entered afterward

Poison acted after isolation

Motive:

Edmund secretly changed his will that afternoon

Clara was completely cut out

She discovered a draft earlier that day

Murder preserves her access to the estate until probate

Key Consistency Constraints:

Cyanide smell fades quickly

No physical struggle

No residue left behind

Clara had intimate routine access

RED HERRINGS (GM GUIDANCE)

Use these to mislead without contradiction:

Red Herring 1 — Julian (Nephew)

Financial desperation

Argument with Edmund

Muddy shoes from the moor

- Timeline disproves opportunity

Red Herring 2 — Dr. Price

Access to drugs

Medical bag

Disagreed with Edmund’s drinking

- All medications accounted for

Red Herring 3 — Fireplace

Burned papers

Suggests destroyed evidence

- Old personal letters only

Red Herring 4 — Evelyn (Housekeeper)

Nervous behavior

Knows hidden passages

- Hiding unrelated personal issue

INTERACTION STYLE

Use second-person narration ("You enter the study...")
Allow:

Free exploration

Object inspection

Dialogue and re-questioning

Confrontation with evidence

NPCs adapt behavior as suspicion increases

Clara remains composed longer than others
"""}

# ========================================
# 8. Alzheimer's 2
# ========================================

dwlite_quests[8] = \
{
  "scenario_for_user": """You are performing Alzheimer's research in the lab on Planet X, analyzing the SEA-AD dataset. You encounter a puzzling pattern: Two individuals with very similar continuous pseudo-progression scores (CPS) show nearly identical global amyloid and tau burden. Despite this, a specific neuronal population behaves very differently between them.

In one brain, V1-specific L4 IT neuron subtypes show a pronounced and early loss. In the other brain, those same L4 IT neurons appear relatively preserved, even at a comparable disease stage.

Your quest is to perform analyses and reasoning to answer the question:
"Why are these specialized L4 IT neurons selectively vulnerable in one case but resilient in another, given comparable disease stage?"
""",
  "scenario_for_system": """### **Current Quest: Gene-Driven Selective Vulnerability in Alzheimer's Disease (Challenge Difficulty)**

This quest evaluates the agent’s ability to identify **cell-intrinsic molecular mechanisms** that explain selective neuronal vulnerability, and to connect gene-expression differences to downstream causal pathways.

---

## Ground Truth (Gold Answer – Hidden from Player)

**Correct explanation:**

The divergent fate of V1-specific L4 IT neurons is driven by **differential expression of a key protective gene**, rather than differences in global pathology or network exposure.

Specifically:

* In the resilient individual, V1 L4 IT neurons show **elevated expression of a mitochondrial quality-control and stress-response gene** (e.g., *HSPA9*, *PINK1*, or a comparable chaperone/mitophagy regulator).
* This gene enhances:
  * Mitochondrial resilience
  * Protein-folding capacity
  * Resistance to tau-induced cellular stress

* In the vulnerable individual, expression of this gene is **selectively reduced in V1 L4 IT neurons**, even though other neuronal populations appear similar.
* Reduced expression leads to:
  * Impaired mitochondrial function
  * Accumulation of misfolded proteins
  * Heightened susceptibility to tau toxicity

As a result, these neurons cross a **cell-intrinsic failure threshold** earlier, producing steep loss despite comparable amyloid, tau, and CPS.

The key insight is that **small, cell-type–specific gene-expression differences can dominate disease outcome**, independently of global pathology.

---

## Causal Pathway (for Simulator Reasoning)

The simulator should internally model the following chain:

Lower gene expression ->  Lower mitochondrial stress handling  ->  Grater proteostasis failure -> Greater tao toxicity sensitivity ->  selective neuron loss

This pathway should emerge only after **integrating multiple lines of evidence**.

---

## Plausible but Incorrect Explanations (Red Herrings)

The simulator should allow investigation of these hypotheses, but ensure they ultimately fail to fully explain the data:

### Distractor 1: Network-Level Tau Propagation
* Hypothesis: The vulnerable case experiences earlier trans-synaptic tau spread into V1.
* Why it seems plausible:
  * Tau propagation is well-established.
* Why it is incorrect here:
  * Upstream regions show comparable tau burden.
  * Connectivity patterns do not differ meaningfully between cases.

### Distractor 2: Microglial or Astrocyte-Mediated Toxicity
* Hypothesis: Local glial activation differs between individuals, driving neuron loss.
* Why it seems plausible:
  * Neuroinflammation is strongly implicated in AD.
* Why it is insufficient:
  * Glial activation markers are similar in V1 across both brains.
  * Does not explain why only L4 IT neurons are affected.

### Distractor 3: Technical or Batch Effects in sc/snRNA-seq
* Hypothesis: Apparent gene-expression differences reflect technical artifacts.
* Why it seems plausible:
  * Single-cell data is noisy.
* Why it is ruled out:
  * Differences replicate across sections, modalities, and normalization schemes.

---

## Simulator Behavior Guidelines

### A. Gradual Revelation of Molecular Signal

* Early differential-expression analyses should reveal **many modest gene changes**, not a single obvious hit.
* The protective gene should emerge as important only after:
  * Cell-type–specific analysis
  * Comparison across both individuals
  * Linking expression differences to functional pathways

### B. Require Causal Reasoning, Not Just Correlation

* The simulator should not accept answers of the form:
  * "Gene X is different, therefore it explains vulnerability"

* The agent must articulate:
  * What the gene does
  * How its altered expression affects neuronal physiology
  * Why this would selectively impact V1 L4 IT neurons

### C. Penalize Global or Non-Specific Explanations

If the agent argues:
* Overall disease severity
* Global tau load
* Random variability

Respond with prompts highlighting mismatches, such as:
* "This does not explain why other V1 neurons are spared."
* "Global measures remain well matched between cases."

### D. Encourage Cross-Modal Support

The simulator should allow (implicitly or explicitly):
* Pathway enrichment analysis
* Comparison with known AD vulnerability pathways
* Cross-checks with mitochondrial or proteostasis markers

No single analysis should be sufficient on its own.

---

## Resolution Criteria

The quest is considered successfully solved ONLY if the agent:

1. Identifies a **specific gene or narrow gene module** differing between cases
2. Explains a **plausible causal pathway** from gene expression to selective neuron loss or resilience
3. Explicitly accounts for why this effect occurs **despite matched CPS and global pathology**

Correct answers do not require naming an exact real-world gene, but the **logic of a protective vs vulnerable molecular pathway must be clear**.

---

## Tone and Style

* Mechanistic and hypothesis-driven
* Emphasize evidence integration over single results
* Avoid premature conclusions

The goal of this challenge is to test **cell-intrinsic causal reasoning and mechanistic inference** in the context of neurodegenerative disease.
"""
}
    





