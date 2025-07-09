import praw

reddit = praw.Reddit(
    client_id="dWaYPYuV8fm8PaIoNSrAKA",
    client_secret=None,
    redirect_uri="http://localhost:8080",
    user_agent="skincare-app"
)

state = "abc"
scopes = ["identity", "read", "mysubreddits", "history"]
auth_url = reddit.auth.url(scopes, state, "permanent")
print("Open this URL in your browser:", auth_url)

redirected_url = input("Paste the full redirect URL after login: ").strip()

from urllib.parse import urlparse, parse_qs
query = urlparse(redirected_url).query
params = parse_qs(query)

if params.get("state", [""])[0] != state:
    raise Exception("❌ State mismatch. Try again.")

auth_code = params.get("code", [""])[0]
if not auth_code:
    raise Exception("❌ Code missing in redirect URL.")

# Step 4: Authorize
refresh_token = reddit.auth.authorize(auth_code)
print("✅ Logged in as:", reddit.user.me())
