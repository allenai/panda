 # Lines starting with '#' are extracted to automatically build documentation_plans.txt. To avoid extraction, offset with a space ' #'
#
### ======================================================================
### Top-level Task: How good is OLMo at addition?
### ======================================================================

# step 1: Ideate three or four *types* of addition problems, to explore where OLMo is string, and where it might be weak..
addition_types = llm_list("List three or four *types* of addition problems, to explore where OLMo is string, and where it might be weak.")
print(addition_types)
 # -> ['Simple arithmetic addition (e.g., 2 + 3)', 'Algebraic addition involving variables (e.g., x + y = z)', ...]

# step 2: For each addition type, generate 10 questions to test OLMo on problems of that type
dataset_parts = []
for addition_type in addition_types:
    dataset_part = create_dataset(f"Generate 10 questions that test this type of addition task: {addition_type}", item_col='question')
    dataset_part['type'] = addition_type
    dataset_parts += [dataset_part]
dataset = pd.concat(dataset_parts, ignore_index=True)
print(dataset)
 # -> question     type
 # 0   1+1?        Simple addition
 # 1   2+2?        Simple addition
 # ..
 # 10  x+2x=?      algebraic
 # ...

# step 3: Have OLMo answer all the questions
answer_questions(dataset, "Answer this addition question: {question}", answer_col='answer', model='olmo')
print(dataset)

# step 4: Score the answers
score_answers(dataset, "Score the answer to the following addition question, between 0 (completely wrong) and 10 (completely correct):\nQuestion: {question}\nAnswer: {answer}", score_col = 'score', score_range=10)
print(dataset)

# step 5: Compute the average scores for each addition type, and put the results in a new Dataframe table
average_scores_df = dataset.groupby('type')['score'].mean().reset_index()
average_scores_df = average_scores_df.rename(columns={'score':'average_score'})
print(average_scores_df)
 # ->   type  average_score
 #   simple addition  0.86
 #   algebraic addit  0.34

# step 6: Articulate some conclusions about which types were easier or harder
prompt = f"""The following table shows OLMo's scores when tested on different types of addition problem:
{average_scores_df.to_string()}
Write a short summary of the findings, in particular which categories OLMo excelled or struggled with (if any)."""
print(call_llm(prompt, model='gpt-4.1'))

# step 7: Write a report
write_report()

#
### ======================================================================
### Top-level Task: How well can OLMo translate into different languages?
### ======================================================================

# step 1. Identify some languages to test OLMo on
languages = llm_list("List the names of some different foreign languages.")
print(languages)

# step 2: Generate a dataset of sentences for testing OLMo's translation capabilities
dataset = create_dataset("Generate 20 sentences that can be used to test machine translation, e.g., 'How are you today?'", item_col='sentence')
print(dataset)

# step 3: For each language, have OLMo translate the source sentence into that language
for language in languages:
    answer_questions(dataset, f"Translate this sentence to {language}: {{sentence}}", answer_col = f"translation_to_{language}", model='olmo')
print(dataset)

# step 4: For each language, score OLMo's translations    
for language in languages:
    score_answers(dataset, f"Score this translation from English to {language}. Give a score between 0 (completely wrong) and 10 (perfect):\nSentence: {{sentence}}\nTranslation: {{translation_to_{language}}}", score_col = f"{language}_score", score_range=10)
print(dataset)

# step 5: Compute OLMo's average translation score for each language
language_info = pd.DataFrame(languages, columns=['language'])
for index, row in language_info.iterrows():
    language = row['language']
    score_col = f"{language}_score"
    average_score = dataset[score_col].mean()
    language_info.at[index,'score'] = average_score
print(language_info)    

# step 6: Data for report: Print the scores showing how well OLMo can translate to the different languages
print("OLMo's translation scores, for different languages:")
language_info_sorted = language_info.sort_values(by='score', ascending=False)  # Sort by 'score' descending
print(language_info_sorted[['language','score']].to_string(index=False))

# step 7: Data for report: Find an example of success and failure for each language
for language in languages:
    sorted = dataset.sort_values(f"{language}_score")
    average_score = dataset[f"{language}_score"].mean()
    best_translation_row = sorted.iloc[-1]          
    worst_translation_row = sorted.iloc[0]
    best_sentence = best_translation_row["sentence"]
    best_translation = best_translation_row[f"translation_to_{language}"]
    best_score = best_translation_row[f"{language}_score"]
    best_score_justification = best_translation_row[f"{language}_score_justification"]    
    worst_sentence = worst_translation_row["sentence"]    
    worst_translation = worst_translation_row[f"translation_to_{language}"]
    worst_score = worst_translation_row[f"{language}_score"]
    worst_score_justification = worst_translation_row[f"{language}_score_justification"]        
    print("\nOLMo's translation to", language, f"(average score: {average_score:.2f}):")
    print(f"Good example (score {best_score:.2f}): \"{best_sentence}\" -> \"{best_translation}\"\nComment: {best_score_justification}\n")
    print(f"Bad example (score {worst_score:.2f}): \"{worst_sentence}\" -> \"{worst_translation}\"\nComment: {worst_score_justification}\n")

# step 8. Write a report on the research
write_report()

#
### ======================================================================
### Top-level Task: Is Olmo or Llama better at telling jokes?
### ======================================================================

# step 1: Generate a dataset of prompts for jokes, e.g., 'Tell me a joke about an interviewee completely misunderstanding the job description.'
dataset = create_dataset("Generate 10 prompts for telling a joke, e.g., 'Tell me a joke about an interviewee completely misunderstanding the job description.'", item_col='prompt')
print(dataset)

# step 2: Have the two different models, olmo and llama, create jokes for each prompt
models = ['olmo','llama']
for model in models:
    answer_questions(dataset, "Generate a short joke, given the following prompt: {prompt}", answer_col = f"{model}_joke", model=model)
print(dataset)    

# step 3: Score the jokes, according to how funny they are    
for model in models:
    score_answers(dataset, f"How funny is this joke? Give a score between 0 (not funny at all) and 10 (absolutely hilarious):\n{{{model}_joke}}", score_col = f"{model}_score", score_range=10)
print(dataset)    

# step 4: Compute the average funniness of each model    
model_info = pd.DataFrame(models, columns=['model'])
for index, row in model_info.iterrows():
    model = row['model']
    score_col = f"{model}_score"
    average_score = dataset[score_col].mean()
    model_info.at[index,'score'] = average_score
print(model_info)    

# step 5: Data for report: Print out the average funniness of each model    
print("Average scores for jokes by different models:")
model_info_sorted = model_info.sort_values(by='score', ascending=False)  # Sort by 'score' descending
print(model_info_sorted[['model','score']].to_string(index=False))

# step 6: Data for report: Print out a good and bad example, for each model
for model in models:
    sorted = dataset.sort_values(f"{model}_score")
    average_score = dataset[f"{model}_score"].mean()
    best_joke_row = sorted.iloc[-1]          
    worst_joke_row = sorted.iloc[0]
    best_joke = best_joke_row[f"{model}_joke"]
    best_score = best_joke_row[f"{model}_score"]
    best_score_justification = best_joke_row[f"{model}_score_justification"]    
    worst_joke = worst_joke_row[f"{model}_joke"]
    worst_score = worst_joke_row[f"{model}_score"]
    worst_score_justification = worst_joke_row[f"{model}_score_justification"]        
    print(f"\n{model}'s jokes", f"(average score: {average_score:.2f}):")
    print("------------------------------")    
    print(f"Good example (score {best_score:.2f}): {best_joke}\nComment: {best_score_justification}\n")
    print(f"Bad example (score {worst_score:.2f}): {worst_joke}\nComment: {worst_score_justification}\n")

# step 7. Write a report on the research
write_report()

#
### ======================================================================
### Top-level Task: How well correlated are OLMo's and Llama's abilities at math?
### ======================================================================

# step 1: Generate a dataset of math problems, with a range of diffulty
dataset = create_dataset("Generate 30 math questions. Generate questions with a range of difficulty, from easy to difficult.")
print(dataset)

# step 2: Have the two language models, olmo and llama, answer the questions
models = ['olmo','llama']
for model in models:
    answer_questions(dataset, "Answer the following math question as concisely as possible: {question}", answer_col = f"{model}_answer", model=model)
print(dataset)    

# step 3: Score the models' answers using LM-as-judge    
for model in models:
    score_answers(dataset, f"Score the answer to the following question between 0 (completely wrong) and 10 (completely correct):\nQuestion: {{question}}\nAnswer: {{{model}_answer}}", score_col = f"{model}_score", score_range=10)
print(dataset)

# step 4: See how well correlated the scores are, using the Spearman rank correlation
spearman_corr = dataset['olmo_score'].corr(dataset['llama_score'], method='spearman')
print(f"Spearman rank correlation between olmo's and llama's scores: {spearman_corr:.3f}")

# step 5: Intepret the result
print(f"That is a {spearman_strength(spearman_corr)} correlation.")

# step 7. Write a report on the research
write_report()

#
### ======================================================================
### Top-level Task: How well can OLMo generate stories? Assess each story on fluency, creativity, and interestingness. What types of story is OLMo best at, in each of those dimensions?
### ======================================================================

# step 1: Generate a dataset of story prompts, e.g., 'Write a story about a cat who lost his tail.'
dataset = create_dataset("Generate 10 story prompts, e.g., 'Write a story about a cat who lost his tail.'", item_col='prompt')
print(dataset)

# step 2: Have OLMo generate stories for each prompt
answer_questions(dataset, "Generate a short story, starting from the following prompt:\n{prompt}", answer_col='story', model='olmo')
print(dataset)

# step 3: Score OLMo's stories along three dimensions: fluency, creativity, and interestingness
dimensions = ['fluency','creativity','interestingness']
for dimension in dimensions:
    score_answers(dataset, f"How good is the following story in terms of {dimension}? Give it a score between 0 ({dimension} is completely lacking) and 10 (perfect {dimension}):\nPrompt: {{prompt}}\nStory: {{story}}", score_col = f"{dimension}_score", score_range=10)
print(dataset)

# step 4: Ideate what types of story prompt resulted in the best OLMo stories. Do this for each dimension.
for dimension in dimensions:
    average_score = dataset[f"{dimension}_score"].mean()    
    best_categories = ideate_categories(dataset, item_col='prompt', score_col=f"{dimension}_score", highlow='high', n=5)              # best categories have HIGH score
    print(f"\nIn terms of {dimension}, OLMo's average score was {average_score:.2f}.")
    if len(best_categories) > 1:
        best_category = best_categories.iloc[1]                  # first row is the best
        best_title = best_category['title']
        best_description = best_category['description']    
        best_score = best_category['score']
        top_examples = examples_in_category(dataset, category_row=best_category, score_col=f"{dimension}_score", highlow='high', n=1)
        best_example = top_examples.iloc[0]
        score_justification_col = f"{dimension}_score_justification"
        print(f"OLMo did particularly well on stories about {best_title} ({best_description}) (average score {best_score:.2f})")
        print(f"For example, for the prompt \"{best_example['prompt']}\", OLMo generated:\n{best_example['story']}")
        print(f"----------\nBecause:\n{best_example[score_justification_col]}")
        print("----------------------------------------\n")
    else:
        print("There were no examples where OLMo did particularly well in this category.")

# step 5. Write a report on the research
write_report()

#
### ======================================================================
### Top-level Task: Characterize OLMo's knowledge about World War II
### ======================================================================

# step 1: Ideate three or four *types* of knowledge about World War II, to explore where OLMo is strong, and where it might be weak.
knowledge_types = llm_list("List three or four *types* of knowledge about World War II, to explore where OLMo is strong, and where it might be weak.")
print(knowledge_types)
 # -> ['historical','biographic',...]

# step 2: For each knowledge type, generate 10 questions to test that knowledge
dataset_parts = []
for knowledge_type in knowledge_types:
    dataset_part = create_dataset(f"Generate 10 questions about World War II that test: {knowledge_type}", item_col='question')
    dataset_part['type'] = knowledge_type
    dataset_parts += [dataset_part]
dataset = pd.concat(dataset_parts, ignore_index=True)
print(dataset)
 # -> question      type
 # 0   When wa...  historical
 # 1   When did... historical
 # ..
 # 10  Who is...   biographic
 # ...

# step 3: Have OLMo answer all the questions
answer_questions(dataset, "Answer this question about World War II: {question}", answer_col='answer', model='olmo')
print(dataset)

# step 4: Score the answers
score_answers(dataset, "Score the answer to the following question about World War II, between 0 (completely wrong) and 10 (completely correct):\nQuestion: {question}\nAnswer: {answer}", score_col = 'score', score_range=10)
print(dataset)

# step 5: Compute the average scores for each knowledge type, and put the results in a new Dataframe table
average_scores_df = dataset.groupby('type')['score'].mean().reset_index()
average_scores_df = average_scores_df.rename(columns={'score':'average_score'})
print(average_scores_df)
 # ->   type  average_score
 #   historical  0.86
 #   biographic  0.34

# step 6: Articulate some conclusions about which types were easier or harder
prompt = f"""The following table shows OLMo's scores when tested on different types of knowledge about World War II:
{average_scores_df.to_string()}
Write a short summary of the findings, in particular which categories OLMo excelled or struggled with (if any)."""
print(call_llm(prompt, model='gpt-4.1'))

# step 7: Write a report
write_report()

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
