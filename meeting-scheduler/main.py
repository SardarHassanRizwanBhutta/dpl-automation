import json
import subprocess
import requests
import re
from prompt_template import get_prompt, get_clarification_prompt
from functions import schedule_meeting
from auth_device_flow import get_access_token
from fuzzywuzzy import fuzz, process

# def call_ollama(prompt: str) -> str:
#     print(f"\n🧠 prompt:\n{prompt}\n")
#     result = subprocess.run(
#         ["ollama", "run", "llama3.1:8b"],
#         input=prompt.encode(),
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE,
#     )
#     output = result.stdout.decode()
#     print("🤖 Model Output:\n", output)
#     return output

def call_ollama(prompt: str) -> str:
    print(f"\n🧠 prompt:\n{prompt}\n")

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3.1:8b",  # or use a smaller/faster one like "mistral"
            "prompt": prompt,
            "stream": False  # set to True if you want streaming
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"🛑 Ollama server error: {response.text}")

    output = response.json()["response"]
    print("🤖 Model Output:\n", output)
    return output

def extract_json(text: str) -> str:
    match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
    if match:
        json_str = match.group(0)
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

def infer_subject_if_missing(arguments: dict) -> dict:
    if not arguments.get("subject") and arguments.get("attendees"):
        attendee = arguments["attendees"][0]
        email = attendee.get("email")
        if email and "@" in email:
            first_part = email.split("@")[0]
            first_name = first_part.split(".")[0].capitalize()
            arguments["subject"] = f"Meeting with {first_name}"
    return arguments

def is_valid(args: dict) -> tuple:
    missing = []

    if not args.get("start_time"):
        missing.append("start_time")

    if not args.get("end_time"):
        missing.append("end_time")

    attendees = args.get("attendees", [])
    if (
        not isinstance(attendees, list)
        or len(attendees) == 0
        or any(a.get("email") in [None, ""] for a in attendees)
    ):
        missing.append("attendees")

    return len(missing) == 0, missing

# ✅ UPDATED: Pass `args` to get dynamic prompt
def get_user_input_for_missing_field(field_name: str, args: dict) -> str:
    clarification_prompt = get_clarification_prompt(field_name, args)
    followup = call_ollama(clarification_prompt)
    print("💬", followup.strip())
    return input("✍️  Your answer: ")

def update_args_with_user_input(args: dict, field_name: str, user_input: str) -> dict:
    if field_name == "attendees":
        emails = [e.strip() for e in user_input.split(",") if e.strip()]
        args["attendees"] = [{"email": e} for e in emails]
    else:
        args[field_name] = user_input.strip()
    return args

# ✅ NEW: Search for user in Azure AD
def search_users_by_name(name, access_token):
    url = f"https://graph.microsoft.com/v1.0/users?$filter=startsWith(displayName,'{name}')"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return [
            {"name": user["displayName"], "email": user["mail"]}
            for user in data.get("value", [])
            if user.get("mail")
        ]
    else:
        raise Exception(f"Graph API error: {response.status_code} - {response.text}")
    
# ✅ NEW: Resolve names to emails in attendees
def resolve_attendee_emails(args, access_token):
    for attendee in args.get("attendees", []):
        if "email" not in attendee and "name" in attendee:
            name = attendee["name"]
            print(f"\n🔍 Searching for users named '{name}'...")
            matches = search_users_by_name(name, access_token)

            if not matches:
                print(f"⚠️ No users found with the name '{name}'.")
                continue
            elif len(matches) == 1:
                attendee["email"] = matches[0]["email"]
                print(f"✅ Found: {matches[0]['name']} - {matches[0]['email']}")
            else:
                print("👥 Multiple users found:")
                for i, user in enumerate(matches, 1):
                    print(f"{i}. {user['name']} - {user['email']}")
                selected = int(input("Select the correct user (1-{}): ".format(len(matches))))
                attendee["email"] = matches[selected - 1]["email"]
                
def main():
    access_token = get_access_token()
    user_input = input("🗓️ Describe the meeting you'd like to schedule:\n")
    prompt = get_prompt(user_input)
    raw_response = call_ollama(prompt)

    try:
        json_str = extract_json(raw_response)
        if not json_str:
            raise ValueError("No JSON found in model output.")

        parsed = json_str

        if parsed.get("function") == "schedule_meeting":
            args = parsed.get("arguments", {})

            # ✅ Infer subject early, if possible
            args = infer_subject_if_missing(args)
            
            is_complete, missing = is_valid(args)

            while not is_complete:
                print(f"\n⚠️ Missing fields: {missing}")

                for field in missing:
                    user_input = get_user_input_for_missing_field(field, args)
                    args = update_args_with_user_input(args, field, user_input)

                    # ✅ If attendees are added now and subject is still missing, infer it
                    if field == "attendees" and not args.get("subject"):
                        args = infer_subject_if_missing(args)

                is_complete, missing = is_valid(args)

            # ✅ Apply Fix 2: infer subject immediately after initial model response
            args = infer_subject_if_missing(args)
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
