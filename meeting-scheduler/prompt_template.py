import json

def get_prompt(user_input: str) -> str:
    return f"""
You are a helpful assistant that schedules Microsoft Teams meetings by calling a function named schedule_meeting.

Your task is to ONLY return valid JSON with the following format:

{{
  "function": "schedule_meeting",
  "arguments": {{
    "subject": "...",
    "start_time": "...",
    "end_time": "...",
    "attendees": [
      {{
        "email": "..."
      }}
    ]
  }}
}}

- Dates and times must be in ISO 8601 format: YYYY-MM-DDTHH:MM:SS
- If the subject is not explicitly mentioned, generate a subject like "Meeting with [first name of recipient]"
  - Use the name part of the email before the `@` symbol to infer the recipient's first name (e.g., `jason.lee@gmail.com` → `"Meeting with Jason"`).
  - Capitalize the first letter of the name.
- If **any other field** is missing (e.g., time, date, attendees), set its value to `null`.
- Do NOT assume or hallucinate any other details.
- Do NOT include any explanation.
- Do NOT use markdown or code blocks. Only output pure JSON.

EXAMPLE:

User request: Schedule a meeting with jane.doe@example.com on May 1, 2025 from 3pm to 4pm.

Response:
{{
  "function": "schedule_meeting",
  "arguments": {{
    "subject": "Meeting with Jane",
    "start_time": "2025-05-01T15:00:00",
    "end_time": "2025-05-01T16:00:00",
    "attendees": [
      {{
        "email": "jane.doe@example.com"
      }}
    ]
  }}
}}

NOW COMPLETE THIS:

User request: {user_input}
""".strip()

def get_clarification_prompt(field: str, current_json: dict) -> str:
    return f"""
You are a helpful assistant helping a user schedule a Microsoft Teams meeting.

A field called "{field}" is missing in the current meeting details.

Your task is to generate a natural follow-up question to ask the user, in plain English, to fill in that specific detail.

The current JSON looks like this:

{json.dumps(current_json, indent=2)}

Guidelines:
- Only ask one brief, natural-sounding question about the missing field "{field}".
- Do NOT say anything about JSON.
- Do NOT include explanations or any prefix like “User:” or “Assistant:”.
- Respond ONLY with the question.

Now, ask a question to fill the missing value for "{field}".
""".strip()
