# r/Kosovo Daily Digest

A GitHub Actions-powered bot that scrapes r/kosovo daily and posts a digest of the best posts to Discord.

## Setup

1. **Clone this repository**
2. **Configure Discord webhook**:
   - Go to your Discord server settings
   - Navigate to **Integrations > Webhooks**
   - Create a new webhook, copy the URL
   - Paste it into `config.yaml`
3. **Customize settings** in `config.yaml`:
   - `min_upvotes`: Minimum upvotes to include
   - `min_age_hours`: Post age filter (2+ hours by default)
   - `top_n`: Number of top posts to show

## Running

### Manual (local)
```bash
pip install -r requirements.txt
python main.py
```

### GitHub Actions
The workflow runs automatically daily at 8:00 UTC. You can also trigger it manually from the Actions tab.

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| min_upvotes | 5 | Minimum upvotes to include a post |
| min_age_hours | 2 | Minimum age in hours before post is included |
| top_n | 5 | Number of top posts to include |

## Project Structure

```
r-kosovo-digest/
├── main.py              # Main script
├── config.yaml          # Configuration
├── requirements.txt    # Python dependencies
└── .github/
    └── workflows/
        └── daily-digest.yml  # GitHub Actions workflow
```
