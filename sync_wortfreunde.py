"""
Sync posts from Wortfreunde to omg.lol weblog.

Usage:
    # List available channels
    python sync_wortfreunde.py channels

    # List posts in a channel
    python sync_wortfreunde.py posts <channel_id>

    # Sync all posts from a channel to omg.lol
    python sync_wortfreunde.py sync <channel_id>

    # Sync a single post by ID
    python sync_wortfreunde.py sync <channel_id> --post-id 228

    # Dry run (preview without publishing)
    python sync_wortfreunde.py sync <channel_id> --dry-run

Environment variables (via .env):
    WORTFREUNDE_API_KEY  — Wortfreunde API token
    OMGLOL_API_KEY       — omg.lol API key
    OMGLOL_ADDRESS       — omg.lol address (e.g. "olivier")
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

from omglol import OmgLol

load_dotenv()

WF_BASE = "https://api.wortfreunde.ch/v1"
SYNC_STATE_FILE = Path(__file__).parent / ".sync_state.json"


def wf_headers() -> dict:
    key = os.environ.get("WORTFREUNDE_API_KEY")
    if not key:
        print("Error: Set WORTFREUNDE_API_KEY in .env or environment")
        sys.exit(1)
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def wf_get(path: str) -> dict:
    resp = requests.get(f"{WF_BASE}{path}", headers=wf_headers())
    resp.raise_for_status()
    return resp.json()


def load_sync_state() -> dict:
    if SYNC_STATE_FILE.exists():
        return json.loads(SYNC_STATE_FILE.read_text())
    return {"synced": {}}


def save_sync_state(state: dict) -> None:
    SYNC_STATE_FILE.write_text(json.dumps(state, indent=2))


def cmd_channels(args: argparse.Namespace) -> None:
    data = wf_get("/channels")
    for ch in data["data"]:
        team = f" [{ch['team']['name']}]" if ch.get("team") else ""
        print(f"  {ch['id']:5d}  {ch['title']:20s}  {ch['platform']:10s}{team}  ({ch['posts_count']} posts)")


def cmd_posts(args: argparse.Namespace) -> None:
    data = wf_get(f"/channels/{args.channel_id}/posts")
    for post in data["data"]:
        status = post["publication_status"]
        date = post["created_at"][:10]
        print(f"  {post['id']:5d}  [{status:9s}]  {date}  {post['title']}")


def _to_markdown(text: str) -> str:
    """Convert Wortfreunde text formatting to proper Markdown."""
    lines = text.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("• "):
            line = "- " + stripped[2:]
        elif stripped.startswith("→ "):
            line = "- " + stripped[2:]
        result.append(line)
    return "\n".join(result)


def cmd_sync(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OMGLOL_API_KEY")
    address = os.environ.get("OMGLOL_ADDRESS")
    if not api_key or not address:
        print("Error: Set OMGLOL_API_KEY and OMGLOL_ADDRESS in .env or environment")
        sys.exit(1)

    client = OmgLol(api_key=api_key, address=address)
    state = load_sync_state()

    # Fetch posts from channel
    data = wf_get(f"/channels/{args.channel_id}/posts")
    posts = data["data"]

    if args.post_id:
        posts = [p for p in posts if p["id"] == args.post_id]
        if not posts:
            print(f"Post {args.post_id} not found in channel {args.channel_id}")
            sys.exit(1)

    if not args.include_drafts:
        posts = [p for p in posts if p["publication_status"] == "published"]

    if not posts:
        print("No posts to sync (use --include-drafts to include draft posts)")
        return

    synced = 0
    for post_summary in posts:
        post_id = str(post_summary["id"])
        updated_at = post_summary["updated_at"]

        # Skip if already synced and not updated
        if not args.force and post_id in state["synced"]:
            if state["synced"][post_id].get("updated_at") == updated_at:
                print(f"  Skipping (unchanged): {post_summary['title']}")
                continue

        # Fetch full post content
        full = wf_get(f"/channels/{args.channel_id}/posts/{post_id}")
        post = full["data"]

        title = post["title"]
        body = _to_markdown(post["body"])
        if post.get("slug"):
            slug = post["slug"]
        else:
            s = title.lower()
            for old, new in [("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")]:
                s = s.replace(old, new)
            slug = re.sub(r"[^\w]+", "-", s).strip("-")[:50].rstrip("-")
        date_str = post.get("published_at") or post["created_at"]
        date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        if args.dry_run:
            print(f"  [dry-run] Would sync: {title} (slug: {slug})")
            continue

        try:
            result = client.create_post(
                title=title,
                content=body,
                slug=slug,
                date=date,
            )
        except Exception as e:
            print(f"  Error syncing '{title}': {e}", file=sys.stderr)
            continue

        print(f"  Synced: {title}")
        print(f"    → https://{address}.weblog.lol{result.location}")

        state["synced"][post_id] = {
            "slug": slug,
            "title": title,
            "updated_at": updated_at,
            "synced_at": datetime.now().isoformat(),
        }
        save_sync_state(state)
        synced += 1
        time.sleep(1)  # rate limit buffer

    print(f"\nDone: {synced} post(s) synced.")


def main():
    parser = argparse.ArgumentParser(
        prog="sync_wortfreunde",
        description="Sync Wortfreunde posts to omg.lol weblog",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("channels", help="List Wortfreunde channels")

    p = sub.add_parser("posts", help="List posts in a channel")
    p.add_argument("channel_id", type=int)

    p = sub.add_parser("sync", help="Sync posts to omg.lol")
    p.add_argument("channel_id", type=int)
    p.add_argument("--post-id", type=int, help="Sync a single post by ID")
    p.add_argument("--dry-run", action="store_true", help="Preview without publishing")
    p.add_argument("--include-drafts", action="store_true", help="Also sync draft posts")
    p.add_argument("--force", action="store_true", help="Re-sync even if unchanged")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"channels": cmd_channels, "posts": cmd_posts, "sync": cmd_sync}[args.command](args)


if __name__ == "__main__":
    main()
