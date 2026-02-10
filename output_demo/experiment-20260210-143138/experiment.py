
# ----------
import random
random.seed(42)
dataset = []
for i in range(5):
    num1 = random.randint(10, 99)
    num2 = random.randint(10, 99)
    correct_answer = num1 + num2
    dataset.append({
        'problem_id': i + 1,
        'num1': num1,
        'num2': num2,
        'problem': f"{num1} + {num2}",
        'correct_answer': correct_answer
    })
print("Generated Dataset of 2-Digit Addition Problems:")
print("=" * 50)
for item in dataset:
    print(f"Problem {item['problem_id']}: {item['problem']} = {item['correct_answer']}")
print("=" * 50)
print(f"Total problems: {len(dataset)}")
print("\nDataset stored in variable 'dataset'")

# ----------

# ----------
print("Querying Claude with addition problems...")
print("=" * 50)
results = []
for item in dataset:
    problem = item['problem']
    
    # Create a prompt for Claude
    prompt = f"What is {problem}? Please provide only the numerical answer."
    
    # Query Claude (using a Claude model)
    response = call_llm(prompt, model='claude-sonnet-4-5-20250929', temperature=0)
    
    # Store the result
    results.append({
        'problem_id': item['problem_id'],
        'problem': problem,
        'correct_answer': item['correct_answer'],
        'claude_response': response
    })
    
    print(f"Problem {item['problem_id']}: {problem}")
    print(f"  Claude's response: {response}")
    print()
print("=" * 50)
print(f"Completed querying Claude for {len(results)} problems")
print("\nResults stored in variable 'results'")

# ----------

# ----------
import re
print("Evaluating Claude's responses...")
print("=" * 50)
correct_count = 0
total_count = len(results)
for result in results:
    problem_id = result['problem_id']
    problem = result['problem']
    correct_answer = result['correct_answer']
    claude_response = result['claude_response']
    
    # Extract numerical answer from Claude's response
    # Look for numbers in the response
    numbers = re.findall(r'-?\d+', claude_response)
    
    if numbers:
        claude_answer = int(numbers[0])  # Take the first number found
    else:
        claude_answer = None
    
    # Check if correct
    is_correct = (claude_answer == correct_answer)
    if is_correct:
        correct_count += 1
    
    # Store evaluation results
    result['claude_answer'] = claude_answer
    result['is_correct'] = is_correct
    
    # Print evaluation for this problem
    status = " CORRECT" if is_correct else " INCORRECT"
    print(f"Problem {problem_id}: {problem}")
    print(f"  Correct answer: {correct_answer}")
    print(f"  Claude's answer: {claude_answer}")
    print(f"  Status: {status}")
    print()
accuracy = (correct_count / total_count) * 100 if total_count > 0 else 0
print("=" * 50)
print("SUMMARY:")
print(f"Total problems: {total_count}")
print(f"Correct answers: {correct_count}")
print(f"Incorrect answers: {total_count - correct_count}")
print(f"Accuracy: {accuracy:.1f}%")
print("=" * 50)
print("\nEvaluation complete. Results updated in 'results' variable.")

# ----------

# ----------
print("\n" + "="*70)
print("FINAL RESULTS: Claude's Performance on 2-Digit Addition")
print("="*70)
print("\nDetailed Results:")
print("-" * 70)
print(f"{'ID':<5} {'Problem':<15} {'Correct':<10} {'Claude':<10} {'Status':<10}")
print("-" * 70)
for result in results:
    problem_id = result['problem_id']
    problem = result['problem']
    correct_answer = result['correct_answer']
    claude_answer = result['claude_answer']
    status = " PASS" if result['is_correct'] else " FAIL"
    
    print(f"{problem_id:<5} {problem:<15} {correct_answer:<10} {claude_answer:<10} {status:<10}")
print("-" * 70)
print("\nPerformance Summary:")
print("-" * 70)
print(f"Total Problems Tested: {total_count}")
print(f"Correct Answers: {correct_count}")
print(f"Incorrect Answers: {total_count - correct_count}")
print(f"Accuracy Rate: {accuracy:.1f}%")
print("-" * 70)
print("\nKey Findings:")
if accuracy == 100:
    print("- Claude achieved perfect accuracy on all 2-digit addition problems")
    print("- All responses were correctly formatted as numerical answers")
    print("- The model demonstrated reliable arithmetic capabilities for this task")
elif accuracy >= 80:
    print(f"- Claude showed strong performance with {accuracy:.1f}% accuracy")
    incorrect_problems = [r for r in results if not r['is_correct']]
    if incorrect_problems:
        print("- Errors occurred on the following problems:")
        for r in incorrect_problems:
            print(f"  - {r['problem']} (answered {r['claude_answer']}, correct: {r['correct_answer']})")
else:
    print(f"- Claude struggled with 2-digit addition, achieving only {accuracy:.1f}% accuracy")
print("="*70)
print()

# ----------

# ----------
print("Generating final report...")
print()
report_path = write_report()
print(f"\nReport generation complete!")
print(f"Report saved to: {report_path}")

# ----------
