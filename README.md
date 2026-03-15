# omglol

Python client and CLI for the [omg.lol](https://omg.lol) API — weblog, pastebin, statuslog, PURLs, DNS, /now page, and more.

## Setup

```bash
uv sync
cp .env.example .env  # add your API key and address
```

Get your API key at [home.omg.lol/account](https://home.omg.lol/account).

## CLI

After `uv sync`, the `omglol` command is available:

```bash
# Publish markdown files to your weblog
omglol post article.md draft.md

# List weblog posts
omglol posts list

# Get a specific post
omglol posts get my-post-slug

# Delete a post
omglol posts delete my-post-slug

# Manage pastes
omglol paste list
omglol paste create my-note "Some content here"
omglol paste get my-note
omglol paste delete my-note

# Post and list statuses
omglol status post "Working on something cool"
omglol status post "Celebrating!" --emoji "🎉"
omglol status list

# Manage PURLs (persistent redirects)
omglol purl list
omglol purl create gh https://github.com/you
omglol purl delete gh

# /now page
omglol now get
omglol now update "Currently learning Rust"

# DNS records
omglol dns list
omglol dns create CNAME www example.com
omglol dns delete <record-id>

# Web page / profile
omglol web get
omglol web update "<h1>Hello</h1>"
omglol web update - < page.html  # read from stdin

# Email forwarding
omglol email get
omglol email set me@example.com

# Profile picture
omglol pfp avatar.png

# Account info
omglol info
```

### Dry run

Preview what would be sent without making changes:

```bash
omglol --dry-run post article.md
omglol --dry-run status post "Test"
omglol --dry-run dns create A @ 1.2.3.4
```

## Library

```python
from omglol import OmgLol

client = OmgLol(api_key="your_key", address="yourname")

# Weblog
client.post_markdown("my-post.md")
client.create_post(title="Hello World", content="This is my post.")
for post in client.list_posts():
    print(post.title, post.location)
client.delete_post("my-post-slug")

# Pastebin
client.create_paste("notes", "Some text")
for paste in client.list_pastes():
    print(paste.title)

# Statuslog
client.post_status("Hello from the API!", emoji="🎉")
for status in client.list_statuses():
    print(status.emoji, status.content)

# PURLs
client.create_purl("gh", "https://github.com/you")
for purl in client.list_purls():
    print(f"{purl.name} → {purl.url}")

# /now page
now = client.get_now()
print(now.content)
client.update_now("Currently building things")

# DNS
for rec in client.list_dns_records():
    print(f"{rec.record_type} {rec.name} → {rec.data}")
client.create_dns_record("CNAME", "www", "example.com")

# Web page / profile
client.update_web("<h1>My page</h1>")

# Email forwarding
client.set_email_forwarding("me@example.com")

# Profile picture
client.upload_pfp("avatar.png")

# Account
info = client.get_address_info()
```

All list/get methods return typed dataclasses (`Post`, `Paste`, `Status`, `Purl`, `DnsRecord`, `NowPage`) instead of raw dicts.

### Markdown frontmatter

Weblog posts can include optional frontmatter:

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

## Development

```bash
uv sync
uv run pytest -v
```

## License

MIT
