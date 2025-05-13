import json
import subprocess
import re
from prompt_template import get_prompt
from functions import schedule_meeting
from auth_device_flow import get_access_token

def call_ollama(prompt: str) -> str:
    print(f"\n🧠 prompt:\n{prompt}\n")
    result = subprocess.run(
        ["ollama", "run", "llama3.1:8b"],
        # ["ollama", "run", "llama3.2:1b"],
        input=prompt.encode(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = result.stdout.decode()
    print("🤖 Model Output:\n", output)
    return output

def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
    if match:
        json_str = match.group(0)
        # Try to fix common errors like a missing closing brace
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            if not json_str.endswith("}"):
                json_str += "}"
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                raise ValueError(f"Malformed JSON: {e}")
    else:
        raise ValueError("No JSON found in model output.")
    
def is_valid(args: dict) -> tuple:
    missing = []

    if not args.get("start_time"):
        missing.append("start_time")

    if not args.get("end_time"):
        missing.append("end_time")

    attendees = args.get("attendees", [])
    # FIXED: Validate that at least one email exists and is not null/empty
    if (
        not isinstance(attendees, list)
        or len(attendees) == 0
        or any(a.get("email") in [None, ""] for a in attendees)
    ):
        missing.append("attendees")

    return len(missing) == 0, missing

def fill_missing_fields(args: dict, missing_fields: list) -> dict:
    for field in missing_fields:
        if field == "start_time":
            args["start_time"] = input("❓ Please enter the meeting start time (e.g., 2025-04-29T22:00:00):\n")
        elif field == "end_time":
            args["end_time"] = input("❓ Please enter the meeting end time (e.g., 2025-04-29T23:00:00):\n")
        elif field == "attendees":
            emails = input("❓ Please enter attendee email(s) separated by commas:\n").split(",")
            args["attendees"] = [{"email": email.strip()} for email in emails if email.strip()]
    return args

def main():
    access_token = get_access_token()
    user_input = input("🗓️ Describe the meeting you'd like to schedule:\n")
    prompt = get_prompt(user_input)
    raw_response = call_ollama(prompt)

    try:
        json_str = extract_json(raw_response)
        if not json_str:
            raise ValueError("No JSON found in model output.")
        # parsed = json.loads(json_str)
        parsed = json_str  # Already a dictionary

        if parsed.get("function") == "schedule_meeting":
            args = parsed.get("arguments", {})
            is_complete, missing = is_valid(args)

            while not is_complete:
                print(f"\n⚠️ Missing fields: {missing}")
                args = fill_missing_fields(args, missing)
                is_complete, missing = is_valid(args)

            print("\n📦 Final JSON Payload:")
            print(json.dumps(args, indent=2))

            result = schedule_meeting(args, access_token)

            print("\n✅ Meeting created successfully!")
            print("🔗 Join URL:", result["joinUrl"])
        else:
            raise ValueError("Unexpected function name in model output.")

    except Exception as e:
        print("❌ Failed to schedule meeting.")
        print(f"Error: {e}")
        print("Raw response:\n", raw_response)
        
if __name__ == "__main__":
    main()
