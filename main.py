import os
import json
import requests
import yaml
from datetime import datetime, timezone
from typing import Optional


def load_config() -> dict:
    config_path = os.environ.get('CONFIG_PATH', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_reddit_posts(subreddit: str = "kosovo") -> list:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    data = response.json()
    posts = []
    
    for post in data['data']['children']:
        p = post['data']
        posts.append({
            'data': {
                'title': p.get('title', ''),
                'permalink': p.get('permalink', ''),
                'score': p.get('score', 0),
                'num_comments': p.get('num_comments', 0),
                'created_utc': p.get('created_utc', 0),
                'link_flair_text': p.get('link_flair_text', ''),
                'url': p.get('url', '')
            }
        })
    
    return posts


def filter_posts(posts: list, min_upvotes: int = 1, min_age_hours: int = 1) -> list:
    now = datetime.now(timezone.utc)
    filtered = []
    
    for post in posts:
        data = post['data']
        created_utc = data['created_utc']
        
        if created_utc == 0:
            continue
            
        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        age_hours = (now - post_time).total_seconds() / 3600
        
        if age_hours < min_age_hours:
            continue
        
        if data['score'] < min_upvotes:
            continue
        
        filtered.append(data)
        print(f"  OK: {data.get('title', '')[:50]} | Score: {data.get('score', 0)} | Age: {age_hours:.1f}h")
    
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
            {"name": "Upvotes", "value": str(post['score']), "inline": True},
            {"name": "Comments", "value": str(post['num_comments']), "inline": True},
        ]
    }
    
    return embed


def post_to_discord(embeds: list, webhook_url: str) -> None:
    if not embeds:
        print("No embeds to post!")
        return
        
    payload = {
        "content": "**r/Kosovo Daily Digest**",
        "embeds": embeds
    }
    
    print(f"Posting to Discord: {len(embeds)} embeds")
    response = requests.post(webhook_url, json=payload, timeout=30)
    print(f"Discord response: {response.status_code}")
    response.raise_for_status()


def main():
    print("Starting r/kosovo digest...")
    
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    reddit_config = config.get('reddit', {})
    discord_config = config.get('discord', {})
    
    min_upvotes = reddit_config.get('min_upvotes', 1)
    min_age_hours = reddit_config.get('min_age_hours', 1)
    top_n = reddit_config.get('top_n', 5)
    
    webhook_url = discord_config.get('webhook_url')
    if not webhook_url:
        print("Error: Discord webhook URL not configured")
        return
    
    print(f"Fetching posts from r/kosovo...")
    
    try:
        all_posts = get_reddit_posts()
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return
    
    print(f"Fetched {len(all_posts)} posts")
    
    if not all_posts:
        print("No posts fetched!")
        return
    
    filtered = filter_posts(all_posts, min_upvotes, min_age_hours)
    print(f"Filtered to {len(filtered)} posts")
    
    if not filtered:
        print("No posts meet criteria, but will post anyway for testing...")
        filtered = all_posts[:top_n]
    
    top_posts = get_top_posts(filtered, top_n)
    most_commented = get_most_commented_post(filtered)
    
    embeds = []
    
    for post in top_posts:
        embeds.append(format_post_embed(post))
    
    if most_commented and most_commented not in top_posts:
        embed = format_post_embed(most_commented)
        embed["title"] = f"Most Discussed: {embed['title']}"
        embeds.append(embed)
    
    embeds = embeds[:10]
    
    try:
        post_to_discord(embeds, webhook_url)
        print("Done!")
    except Exception as e:
        print(f"Error posting to Discord: {e}")


if __name__ == "__main__":
    main()
