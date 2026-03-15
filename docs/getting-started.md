# Getting Started with omglol

This guide walks you through setting up the omglol client and publishing your first content to [omg.lol](https://omg.lol).

## Prerequisites

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/) package manager
- An [omg.lol](https://omg.lol) account with an address

## 1. Get your API key

1. Log in at [home.omg.lol](https://home.omg.lol)
2. Go to [Account Settings](https://home.omg.lol/account)
3. Scroll down to **API Key** and copy it

## 2. Install

Clone the repository and install dependencies:

```bash
git clone https://github.com/dkd-dobberkau/omglol.git
cd omglol
uv sync
```

Or install directly from the repository:

```bash
uv pip install git+https://github.com/dkd-dobberkau/omglol.git
```

## 3. Configure

Create a `.env` file with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
OMGLOL_API_KEY=your-api-key-here
OMGLOL_ADDRESS=yourname
```

The client loads these automatically on startup. Alternatively, you can export them as environment variables:

```bash
export OMGLOL_API_KEY=your-api-key-here
export OMGLOL_ADDRESS=yourname
```

## 4. Verify your setup

Check that everything works by fetching your address info:

```bash
omglol info
```

You should see your account details. If you get an error, double-check your API key and address.

## 5. Your first weblog post

Create a markdown file called `hello.md`:

```markdown
---
title: Hello World
date: 2026-03-15 12:00
slug: hello-world
---

This is my first post published via the omglol CLI!
```

Preview it with `--dry-run`, then publish:

```bash
# Preview (no changes made)
omglol --dry-run post hello.md

# Publish for real
omglol post hello.md
```

Your post is now live at `https://yourname.weblog.lol/hello-world`.

List all your posts to confirm:

```bash
omglol posts list
```

## 6. Post a status

Share what you're up to:

```bash
omglol status post "Just set up the omglol CLI!"
omglol status post "Celebrating!" --emoji "🎉"
```

See all your statuses:

```bash
omglol status list
```

## 7. Create a paste

Pastes are great for sharing snippets:

```bash
# Inline content
omglol paste create my-snippet "print('hello from omg.lol')"

# From stdin (use '-' as content)
echo "some longer content" | omglol paste create my-note -
```

Your paste is available at `https://yourname.paste.lol/my-snippet`.

```bash
# Read it back
omglol paste get my-snippet

# List all pastes
omglol paste list
```

## 8. Set up a PURL

PURLs are persistent URL redirects — handy for short links:

```bash
omglol purl create github https://github.com/yourname
```

Now `https://yourname.url.lol/github` redirects to your GitHub profile.

## 9. Update your /now page

The [/now page](https://nownownow.com/about) tells people what you're focused on:

```bash
omglol now update "Learning Python, building CLI tools, reading sci-fi."
```

Read it back:

```bash
omglol now get
```

## Using as a Python library

You can also use omglol directly in your Python scripts:

```python
from omglol import OmgLol

client = OmgLol(api_key="your-key", address="yourname")

# Publish a markdown file
client.post_markdown("hello.md")

# Create a post programmatically
client.create_post(
    title="Automated Post",
    content="This was published from a Python script.",
)

# List posts — returns typed Post objects
for post in client.list_posts():
    print(f"{post.title} — {post.location}")

# Create a paste
client.create_paste("config", "key = value")

# Post a status
client.post_status("Automating my omg.lol workflow!")
```

All methods return typed dataclasses (`Post`, `Paste`, `Status`, `Purl`, `DnsRecord`, `NowPage`) with attribute access. The original API response is always available via the `.raw` dict.

## Available commands

| Command | Description |
|---------|-------------|
| `omglol post <files...>` | Publish markdown files to weblog |
| `omglol posts list\|get\|delete` | Manage weblog posts |
| `omglol paste list\|get\|create\|delete` | Manage pastes |
| `omglol status post\|list` | Manage statuslog |
| `omglol purl list\|create\|delete` | Manage PURLs |
| `omglol now get\|update` | Manage /now page |
| `omglol dns list\|create\|delete` | Manage DNS records |
| `omglol web get\|update` | Manage web page / profile |
| `omglol email get\|set` | Manage email forwarding |
| `omglol pfp <file>` | Upload profile picture |
| `omglol info` | Show account info |

Add `--dry-run` before any command to preview without making changes.

Use `--help` on any command for details:

```bash
omglol --help
omglol paste --help
omglol paste create --help
```

## Next steps

- Explore the full [omg.lol API docs](https://api.omg.lol)
- Set up a cron job to auto-publish posts from a folder
- Use the library in a static site generator pipeline
- Manage your DNS records programmatically
