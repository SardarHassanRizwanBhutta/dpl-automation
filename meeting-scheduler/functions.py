# functions.py
import requests

def schedule_meeting(args, access_token):
    payload = {
        "subject": args["subject"],
        "start": {
            "dateTime": args["start_time"],
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": args["end_time"],
            "timeZone": "UTC"
        },
        "attendees": [
            {
                "emailAddress": {
                    "address": attendee["email"],
                    # **({"name": attendee["name"]} if "name" in attendee and attendee["name"] else {})
                },
                "type": "required"
            }
            for attendee in args["attendees"]
        ],
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness"
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    response = requests.post("https://graph.microsoft.com/v1.0/me/events", headers=headers, json=payload)

    if response.status_code == 201:
        meeting_info = response.json()
        return {
            "joinUrl": meeting_info.get("onlineMeeting", {}).get("joinUrl"),
            "subject": payload["subject"],
            "start": payload["start"]["dateTime"],
            "end": payload["end"]["dateTime"],
            "attendees": [a["emailAddress"]["address"] for a in payload["attendees"]]
        }
    else:
        raise Exception(f"Failed to create meeting: {response.status_code}, {response.text}")
