import json
import requests
from functions import get_weather, calculate_sum
from prompt_template import PROMPT_TEMPLATE

def call_ollama(prompt: str, model: str = "deepseek-r1:1.5b"):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)

    print(f"Status Code: {response.status_code}")
    print(f"Response JSON: {response.text}")

    if response.status_code != 200:
        raise RuntimeError("Ollama API call failed")

    data = response.json()
    return data["response"]

def handle_function_call(output: str):
    try:
        data = json.loads(output)
        func_name = data.get("function")
        args = data.get("arguments", {})

        if func_name == "get_weather":
            return get_weather(**args)
        elif func_name == "calculate_sum":
            return calculate_sum(**args)
        else:
            return "Unknown function."
    except Exception as e:
        return f"Failed to parse function call: {e}\nOutput: {output}"

def main():
    user_input = input("User: ")
    prompt = PROMPT_TEMPLATE.format(user_input=user_input)

    response = call_ollama(prompt)
    print("\n[Raw LLM Output]:", response)

    result = handle_function_call(response)
    print("\n[Function Result]:", result)

if __name__ == "__main__":
    main()
