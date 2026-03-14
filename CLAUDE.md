# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Single-file Python API client for [omg.lol](https://omg.lol), focused on weblog management and markdown publishing. The entire codebase is `omglol.py`.

## Dependencies

- Python 3.10+ (uses `X | None` union syntax)
- `requests` library (only external dependency)

## Running

```bash
# Publish markdown files via CLI
python omglol.py <api_key> <address> <file.md> [file2.md ...]

# Library usage
from omglol import OmgLol
client = OmgLol(api_key="...", address="yourname")
```

## Architecture

`OmgLol` class wraps the omg.lol REST API (`https://api.omg.lol`):

- **`_request()`** — central HTTP method; handles auth headers, JSON parsing, and error extraction via `OmgLolError`
- **Weblog** — `list_posts`, `get_post`, `get_latest_post`, `create_post`, `delete_post`, `post_markdown`
- **Statuslog** — `post_status`, `list_statuses`
- **Account** — `get_address_info`, `get_service_info`

`post_markdown()` parses optional YAML-like frontmatter (`title`, `date`, `slug`) from `.md` files, falls back to the first H1 heading as the title.

`create_post()` composes the omg.lol-specific source format (Date/Slug header + markdown body) and sends it as `text/plain`.

## API Notes

- The omg.lol API returns `{ request: { success: bool }, response: { ... } }` — error checking is in `_request()`
- New posts use the slug as `entry_id` by default
- `Content-Type` switches between `application/json` (default session header) and `text/plain` (for weblog post body)
