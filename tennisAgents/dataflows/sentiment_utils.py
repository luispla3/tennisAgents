import os
import requests
import datetime
import os
import praw
from praw import Reddit
from dotenv import load_dotenv

load_dotenv()


reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def analyze_sentiment(text):
    if any(w in text.lower() for w in ["amazing", "great", "win", "dominated"]):
        return "positive"
    elif any(w in text.lower() for w in ["terrible", "injured", "awful", "choke"]):
        return "negative"
    else:
        return "neutral"

def fetch_reddit_sentiment(player_name: str, limit: int = 10) -> dict:
    subreddit = reddit.subreddit("tennis")
    posts = subreddit.search(player_name, limit=limit)

    sentiments = {"positive": 0, "negative": 0, "neutral": 0, "examples": []}

    for post in posts:
        text = post.title + ". " + post.selftext
        sentiment = analyze_sentiment(text)
        sentiments[sentiment] += 1
        sentiments["examples"].append({
            "text": text[:100] + "..." if len(text) > 100 else text,
            "sentiment": sentiment
        })

    return sentiments

def fetch_reddit_sentiment(player_name: str, subreddit: str = "tennis", limit: int = 10) -> dict:

    reddit = Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

    posts = reddit.subreddit(subreddit).search(player_name, limit=limit)
    sentiments = {"positive": 0, "negative": 0, "neutral": 0, "examples": []}

    for post in posts:
        text = post.title + ". " + post.selftext
        sentiment = analyze_sentiment(text)
        sentiments[sentiment] += 1
        sentiments["examples"].append({
            "text": text[:100] + "..." if len(text) > 100 else text,
            "sentiment": sentiment
        })

    return sentiments
