# omglol

Python API client for [omg.lol](https://omg.lol) — weblog management and markdown publishing.

## Setup

```bash
uv sync
cp .env.example .env  # add your API key and address
```

Get your API key at [home.omg.lol/account](https://home.omg.lol/account).

## Usage

### CLI

```bash
uv run python omglol.py post.md [post2.md ...]
```

### Library

```python
from omglol import OmgLol

client = OmgLol(api_key="your_key", address="yourname")

# Publish a markdown file
client.post_markdown("my-post.md")

# Create a post directly
client.create_post(title="Hello World", content="This is my post.")

# List all posts
for entry in client.list_posts():
    print(entry["title"], entry["location"])

# Post a status
client.post_status("Hello from the API!")

# Delete a post
client.delete_post("my-post-slug")
```

### Markdown frontmatter

Posts can include optional frontmatter:

```markdown
---
title: My Post Title
date: 2026-03-14 12:00
slug: custom-slug
---

Body content here...
```

If no frontmatter is present, the first `# Heading` is used as the title.

## Environment variables

| Variable | Description |
|---|---|
| `OMGLOL_API_KEY` | Your omg.lol API key |
| `OMGLOL_ADDRESS` | Your omg.lol address (e.g. `olivier`) |
