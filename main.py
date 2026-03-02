import os
import json
import requests
import yaml
from datetime import datetime, timezone, timedelta
from typing import Optional


def load_config() -> dict:
    config_path = os.environ.get('CONFIG_PATH', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_reddit_posts(subreddit: str = "kosovo", limit: int = 100) -> list:
    url = f"https://old.reddit.com/r/{subreddit}/top.json"
    params = {"t": "day", "limit": limit}
    headers = {"User-Agent": "r/KosovoDailyDigest/1.0"}
    
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    return data['data']['children']


def is_old_enough(post_created_utc: int, min_hours: int = 2) -> bool:
    post_time = datetime.fromtimestamp(post_created_utc, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age = now - post_time
    return age.total_seconds() >= (min_hours * 3600)


def filter_posts(posts: list, min_upvotes: int = 1, min_age_hours: int = 2) -> list:
    filtered = []
    for post in posts:
        data = post['data']
        created_utc = data['created_utc']
        
        if not is_old_enough(created_utc, min_age_hours):
            continue
        
        if data['score'] < min_upvotes:
            continue
        
        filtered.append(data)
    
    return filtered


def get_top_posts(posts: list, top_n: int = 5) -> list:
    sorted_by_upvotes = sorted(posts, key=lambda x: x['score'], reverse=True)
    return sorted_by_upvotes[:top_n]


def get_most_commented_post(posts: list) -> Optional[dict]:
    if not posts:
        return None
    return max(posts, key=lambda x: x['num_comments'])


def format_post_embed(post: dict) -> dict:
    title = post['title'][:256]
    url = f"https://reddit.com{post['permalink']}"
    flair = post.get('link_flair_text', '')
    
    embed = {
        "title": f"{flair}: {title}" if flair else title,
        "url": url,
        "color": 16744448,
        "fields": [
            {"name": "⬆️ Upvotes", "value": str(post['score']), "inline": True},
            {"name": "💬 Comments", "value": str(post['num_comments']), "inline": True},
        ]
    }
    
    if post.get('thumbnail') and post['thumbnail'].startswith('http'):
        embed["thumbnail"] = {"url": post['thumbnail']}
    
    return embed


def post_to_discord(embeds: list, webhook_url: str) -> None:
    payload = {
        "content": "📊 **r/Kosovo Daily Digest**",
        "embeds": embeds
    }
    
    response = requests.post(webhook_url, json=payload)
    response.raise_for_status()


def main():
    config = load_config()
    
    reddit_config = config.get('reddit', {})
    discord_config = config.get('discord', {})
    
    min_upvotes = reddit_config.get('min_upvotes', 5)
    min_age_hours = reddit_config.get('min_age_hours', 2)
    top_n = reddit_config.get('top_n', 5)
    
    webhook_url = discord_config.get('webhook_url')
    if not webhook_url:
        raise ValueError("Discord webhook URL not configured")
    
    print("Fetching posts from r/kosovo...")
    all_posts = get_reddit_posts()
    print(f"Fetched {len(all_posts)} posts")
    
    filtered = filter_posts(all_posts, min_upvotes, min_age_hours)
    print(f"Filtered to {len(filtered)} posts (min {min_upvotes} upvotes, {min_age_hours}h old)")
    
    if not filtered:
        print("No posts meet the criteria. Skipping Discord post.")
        return
    
    top_posts = get_top_posts(filtered, top_n)
    most_commented = get_most_commented_post(filtered)
    
    embeds = []
    
    for post in top_posts:
        embeds.append(format_post_embed(post))
    
    if most_commented and most_commented not in top_posts:
        embed = format_post_embed(most_commented)
        embed["title"] = f"💬 Most Discussed: {embed['title']}"
        embeds.append(embed)
    
    embeds = embeds[:10]
    
    print(f"Posting {len(embeds)} posts to Discord...")
    post_to_discord(embeds, webhook_url)
    print("Done!")


if __name__ == "__main__":
    main()
