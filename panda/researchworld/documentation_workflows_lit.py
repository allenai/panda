#
### ======================================================================
### Top-level Task: Generate a literature review about the topic: To what extent do LLMs have a Theory of Mind?
### ======================================================================

# step 1. Find papers about the extent to which LLMs have a Theory of Mind
task = "To what extent do LLMs have a Theory of Mind?"
paper_ids = find_paper_ids(task)
print(paper_ids)

# step 2. Collect summaries of those papers
summaries = ""
for paper_id in paper_ids:
    summary = summarize_paper(paper_id)
    if summary:
        summaries += summary

# step 3: Identify the main themes in those summaries
prompt = "Identify some common themes/dimensions of the following papers:" + summaries
themes = llm_list(prompt)

# step 4: For each theme, generate a paragraph summarizing whe paper summaries say about it
report_paragraphs = {}
for theme in themes:
    prompt = f"Read the following paper summaries, and then write a single paragraph summarizing what they say about the following theme: {theme}" + summaries
    report_paragraphs[theme] = call_llm(prompt)

# step 5: Collect those thematic paragraphs into a final report
title = task + ": A report"
report = title + "\n" + "-" * len(title) + "\n\n"
for theme in themes:
    report += theme + "\n"
    report += "-" * len(theme) + "\n"
    report += report_paragraphs[theme] + "\n\n"
print(report)
