import os
import json
import requests
import yaml
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional


def load_config() -> dict:
    config_path = os.environ.get('CONFIG_PATH', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_reddit_posts(subreddit: str = "kosovo", limit: int = 50) -> list:
    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    posts = []
    
    for item in root.findall('.//item'):
        title = item.find('title').text
        link = item.find('link').text
        pub_date = item.find('pubDate').text
        comments = item.find('{http://www.reddit.com/feed/}num_comments')
        
        score_elem = item.find('{http://www.reddit.com/feed/}score')
        upvote = int(score_elem.text) if score_elem is not None else 0
        num_comments = int(comments.text) if comments is not None else 0
        
        created_utc = datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z').timestamp()
        
        posts.append({
            'data': {
                'title': title,
                'permalink': link.replace('https://reddit.com', ''),
                'score': upvote,
                'num_comments': num_comments,
                'created_utc': created_utc,
                'link_flair_text': '',
                'url': link
            }
        })
    
    return posts


def is_old_enough(post_created_utc: int, min_hours: int = 2) -> bool:
    post_time = datetime.fromtimestamp(post_created_utc, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    age = now - post_time
    return age.total_seconds() >= (min_hours * 3600)


def filter_posts(posts: list, min_upvotes: int = 1, min_age_hours: int = 2) -> list:
    filtered = []
    now = datetime.now(timezone.utc)
    for post in posts:
        data = post['data']
        created_utc = data['created_utc']
        
        post_time = datetime.fromtimestamp(created_utc, tz=timezone.utc)
        age_hours = (now - post_time).total_seconds() / 3600
        print(f"  Post: {data.get('title', 'N/A')[:50]}... | Score: {data.get('score', 0)} | Age: {age_hours:.1f}h")
        
        if age_hours < min_age_hours:
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
    print("Starting r/kosovo digest...")
    
    try:
        config = load_config()
    except Exception as e:
        print(f"Error loading config: {e}")
        return
    
    reddit_config = config.get('reddit', {})
    discord_config = config.get('discord', {})
    
    min_upvotes = reddit_config.get('min_upvotes', 5)
    min_age_hours = reddit_config.get('min_age_hours', 2)
    top_n = reddit_config.get('top_n', 5)
    
    webhook_url = discord_config.get('webhook_url')
    if not webhook_url or webhook_url == "YOUR_DISCORD_WEBHOOK_URL":
        print("Error: Discord webhook URL not configured")
        return
    
    print(f"Fetching posts from r/kosovo (min_upvotes={min_upvotes}, min_age_hours={min_age_hours})...")
    
    try:
        all_posts = get_reddit_posts()
    except Exception as e:
        print(f"Error fetching posts: {e}")
        return
    
    print(f"Fetched {len(all_posts)} posts")
    
    print("Sample post:", all_posts[0] if all_posts else "None")
    
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
    
    try:
        print(f"Posting {len(embeds)} posts to Discord...")
        post_to_discord(embeds, webhook_url)
        print("Done!")
    except Exception as e:
        print(f"Error posting to Discord: {e}")


if __name__ == "__main__":
    main()
