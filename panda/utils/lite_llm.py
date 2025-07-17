
import os
from litellm import completion

# set env PEC Should already be set
# os.environ["ANTHROPIC_API_KEY"] = "your-api-key"


'''
EXAMPLE:
In [1]: print(get_litellm_response('Write me a Python program to sum all the integers less than 20. Return your answer in a JSON structure of the form {"program":PYTHON_CODE}. Do not include any additional commentary or explanation.'))
{
"program": """
sum = 0
for i in range(20):
    sum += i
print(sum)
"""
}
'''
def call_litellm(prompt, api_key=None, model="claude-3-5-sonnet-20240620"):
    messages = [{"role": "user", "content": "You are a helpful assistant"},{"role": "user", "content": prompt}]
    try:
        response = completion(model=model, messages=messages)
        if response and response.choices and response.choices[0].message and response.choices[0].message.content:
            return response.choices[0].message.content
        else:
            return None  # Or raise an exception if you prefer
    except Exception as e:
        print(f"Error getting response from LiteLLM: {e}")
        return None  # Or raise an exception if you prefer


    
