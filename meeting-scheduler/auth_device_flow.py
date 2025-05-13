import os
from msal import PublicClientApplication
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def get_access_token():
    # getting the environment variable
    client_id = os.getenv("CLIENT_ID") 
    tenant_id = os.getenv("TENANT_ID")
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scopes = ["Calendars.ReadWrite", "OnlineMeetings.ReadWrite"]

    app = PublicClientApplication(client_id, authority=authority)

    flow = app.initiate_device_flow(scopes=scopes)
    if "user_code" not in flow:
        raise Exception("Failed to create device flow")

    print(f"🔐 Go to {flow['verification_uri']} and enter code: {flow['user_code']}")

    result = app.acquire_token_by_device_flow(flow)

    if "access_token" in result:
        print("✅ Access token acquired!", result["access_token"])
        return result["access_token"]
    else:
        print("❌ Error getting access token:")
        print(result.get("error_description"))
        return None
