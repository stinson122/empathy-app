import praw

reddit = praw.Reddit(
    client_id="dWaYPYuV8fm8PaIoNSrAKA",
    client_secret=None,
    redirect_uri="http://localhost:8080",
    user_agent="skincare-app"
)

subreddit = reddit.subreddit("BeautyTalkPH")

print("🧴 Top 5 Hot Posts from r/BeautyTalkPH:\n")
for post in subreddit.hot(limit=5):
    print("Title:", post.title)
    print("Upvotes:", post.score)
    print("Comments:", post.num_comments)
    print("Link:", post.url)
    print("—" * 40)
