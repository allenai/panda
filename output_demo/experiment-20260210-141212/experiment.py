
# ----------
models = [
    'gpt-4o-mini',
    'claude-sonnet-4-5-20250929',
    'together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo'
]
prompt = "What is 2 + 2?"
results = {}
print("Comparing 3 LLMs on: 'What is 2 + 2?'")
print("=" * 60)
print()
for model in models:
    print(f"Querying {model}...")
    response = call_llm(prompt, model, temperature=0)
    results[model] = response
    print(f"Model: {model}")
    print(f"Response: {response}")
    print("-" * 60)
    print()
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for model, response in results.items():
    print(f"\n{model}:")
    print(f"  {response}")
write_report()

# ----------
