import os
import praw
import csv
import json
from collections import defaultdict

# This scrapes from entire reddit, not just r/BeautyTalkPh. Ignore for now.

reddit = praw.Reddit(
    # change this
    client_id="Wt3DQHzvtI4_poBQ58Rn2g",
    client_secret="ilhFDto6TafES55zhDrQPJnyJ28ZOw",
    password="Dlsugrad#12",
    user_agent="script:urs:v1.0",
    username="Successful_Body674",
)

# Read product keywords from products.txt
with open("products.txt", "r", encoding="utf-8") as file:
    products = [line.strip() for line in file.readlines() if line.strip()]

scraped_data = []

for product in products:
    posts_data = []
    for submission in reddit.subreddit("all").search(product, limit=5):
        submission.comments.replace_more(limit=0)
        comments = [comment.body for comment in submission.comments.list()[:5]]

        posts_data.append({
            "title": submission.title,
            "content": submission.selftext,
            "url": submission.url,
            "comments": comments
        })

    scraped_data.append({
        "product": product,
        "posts": posts_data
    })

# Export to JSON (Frontend public folder)
json_path = os.path.join("..", "frontend", "public", "scraped.json")
with open(json_path, "w", encoding="utf-8") as jsonfile:
    json.dump(scraped_data, jsonfile, ensure_ascii=False, indent=2)

# Export to CSV
csv_path = "scraped.csv"
with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["Product", "Post Title", "Content", "Comment"])
    for product in scraped_data:
        for post in product["posts"]:
            for comment in post["comments"]:
                writer.writerow([product["product"], post["title"], post["content"], comment])

print("Scraping complete. Data saved to JSON and CSV.")