"""
omg.lol API client
Focused on weblog management and markdown publishing.

Usage:
    client = OmgLol(api_key="your_key", address="yourname")

    # Post a markdown file
    client.post_markdown("my-post.md")

    # Or post content directly
    client.create_post(title="Hello World", content="# Hello\n\nThis is my post.")

    # List all posts
    for post in client.list_posts():
        print(post.title, post.location)
"""

import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


class OmgLolError(Exception):
    pass


# ── Data models ──────────────────────────────────────────────────────────────


@dataclass
class Post:
    entry_id: str = ""
    title: str = ""
    slug: str = ""
    location: str = ""
    source: str = ""
    body: str = ""
    date: str = ""
    status: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Post":
        return cls(
            entry_id=data.get("entry") or data.get("entry_id", ""),
            title=data.get("title", ""),
            slug=data.get("slug", ""),
            location=data.get("location", ""),
            source=data.get("source", ""),
            body=data.get("body", ""),
            date=data.get("date", ""),
            status=data.get("status", ""),
            raw=data,
        )


@dataclass
class Paste:
    title: str = ""
    content: str = ""
    modified_on: str = ""
    listed: bool = True
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Paste":
        return cls(
            title=data.get("title", ""),
            content=data.get("content", ""),
            modified_on=data.get("modified_on", ""),
            listed=bool(data.get("listed", True)),
            raw=data,
        )


@dataclass
class Status:
    id: str = ""
    emoji: str = ""
    content: str = ""
    created: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Status":
        return cls(
            id=data.get("id", ""),
            emoji=data.get("emoji", ""),
            content=data.get("content", ""),
            created=data.get("created", ""),
            raw=data,
        )


@dataclass
class Purl:
    name: str = ""
    url: str = ""
    listed: bool = True
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "Purl":
        return cls(
            name=data.get("name", ""),
            url=data.get("url", ""),
            listed=bool(data.get("listed", True)),
            raw=data,
        )


@dataclass
class DnsRecord:
    id: str = ""
    record_type: str = ""
    name: str = ""
    data: str = ""
    ttl: int = 3600
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "DnsRecord":
        return cls(
            id=data.get("id", ""),
            record_type=data.get("type", ""),
            name=data.get("name", ""),
            data=data.get("data", ""),
            ttl=int(data.get("ttl", 3600)),
            raw=data,
        )


@dataclass
class NowPage:
    content: str = ""
    listed: bool = True
    updated: str = ""
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: dict) -> "NowPage":
        return cls(
            content=data.get("content", ""),
            listed=bool(data.get("listed", True)),
            updated=data.get("updated", ""),
            raw=data,
        )


class OmgLol:
    BASE_URL = "https://api.omg.lol"

    def __init__(self, api_key: str, address: str):
        self.address = address
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    MAX_RETRIES = 3
    RETRY_BACKOFF = 1.0  # seconds, doubled each retry

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.BASE_URL}{path}"
        last_exc = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = self.session.request(method, url, **kwargs)
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", self.RETRY_BACKOFF * 2**attempt))
                    time.sleep(retry_after)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if not data.get("request", {}).get("success", True):
                    raise OmgLolError(data.get("response", {}).get("message", "Unknown error"))
                return data.get("response", data)
            except requests.ConnectionError as exc:
                last_exc = exc
                time.sleep(self.RETRY_BACKOFF * 2**attempt)
        raise last_exc or OmgLolError("Max retries exceeded")

    # ── Weblog ────────────────────────────────────────────────────────────────

    def list_posts(self) -> list[Post]:
        """Return all weblog entries."""
        response = self._request("GET", f"/address/{self.address}/weblog/entries")
        return [Post.from_dict(e) for e in response.get("entries", [])]

    def get_post(self, entry_id: str) -> Post:
        """Fetch a single weblog entry by ID."""
        response = self._request("GET", f"/address/{self.address}/weblog/entry/{entry_id}")
        return Post.from_dict(response.get("entry", response))

    def get_latest_post(self) -> Post:
        """Fetch the latest published post (no auth required)."""
        response = self._request("GET", f"/address/{self.address}/weblog/post/latest")
        return Post.from_dict(response.get("post", response))

    def create_post(
        self,
        title: str,
        content: str,
        date: datetime | None = None,
        slug: str | None = None,
        entry_id: str | None = None,
    ) -> Post:
        """
        Create or update a weblog entry.

        The omg.lol weblog format uses a frontmatter block delimited by ---:

            ---
            Date: 2025-03-14 12:00
            Slug: optional-custom-slug
            ---

            # Your title here

            Body content in markdown...

        Args:
            title:    Post title (used as the H1 heading).
            content:  Markdown body (without the title line).
            date:     Publication datetime (defaults to now).
            slug:     Optional URL slug (defaults to slugified title).
            entry_id: Existing entry ID to update, or None to create new.
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y-%m-%d %H:%M")

        if slug is None:
            slug = re.sub(r"[^\w]+", "-", title.lower()).strip("-")

        # Compose the omg.lol weblog source format with --- delimiters
        frontmatter = f"---\nDate: {date_str}\nSlug: {slug}\n---"
        body = f"# {title}\n\n{content.strip()}"
        source = f"{frontmatter}\n\n{body}"

        if entry_id is None:
            entry_id = slug  # omg.lol accepts a slug as the entry ID for new posts

        response = self._request(
            "POST",
            f"/address/{self.address}/weblog/entry/{entry_id}",
            data=source.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
        )
        return Post.from_dict(response.get("entry", response))

    def post_markdown(self, filepath: str | Path, entry_id: str | None = None) -> Post:
        """
        Publish a markdown file to your omg.lol weblog.

        The file may optionally start with a YAML-like frontmatter block:

            ---
            title: My Post Title
            date: 2025-03-14 12:00
            slug: my-post-title
            ---

            # My Post Title

            Body content here...

        If no frontmatter is present, the first H1 heading is used as
        the title, and the date defaults to now.

        Args:
            filepath: Path to the .md file.
            entry_id: Existing entry ID to update (optional).

        Returns:
            The created/updated Post.
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        raw = path.read_text(encoding="utf-8").strip()

        # Parse optional frontmatter
        title = None
        date = None
        slug = None

        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                fm_block = parts[1].strip()
                body = parts[2].strip()
                for line in fm_block.splitlines():
                    if ":" in line:
                        key, _, val = line.partition(":")
                        key = key.strip().lower()
                        val = val.strip()
                        if key == "title":
                            title = val
                        elif key == "date":
                            try:
                                date = datetime.fromisoformat(val)
                            except ValueError:
                                pass
                        elif key == "slug":
                            slug = val
            else:
                body = raw
        else:
            body = raw

        # Fall back to first H1 in the body as title
        if title is None:
            for line in body.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break

        if title is None:
            title = path.stem.replace("-", " ").replace("_", " ").title()

        # Strip leading H1 from body to avoid duplication (create_post adds it)
        body_lines = body.splitlines()
        if body_lines and body_lines[0].strip() == f"# {title}":
            body = "\n".join(body_lines[1:]).strip()

        print(f"Publishing: '{title}' from {path.name}")
        result = self.create_post(title=title, content=body, date=date, slug=slug, entry_id=entry_id)
        print(f"  Published at: https://{self.address}.weblog.lol{result.location}")
        return result

    def delete_post(self, entry_id: str) -> str:
        """Permanently delete a weblog entry. Returns the confirmation message."""
        response = self._request("DELETE", f"/address/{self.address}/weblog/delete/{entry_id}")
        return response.get("message", "Deleted.")

    # ── Weblog config ─────────────────────────────────────────────────────────

    def get_weblog_config(self) -> dict:
        """Retrieve weblog configuration."""
        return self._request("GET", f"/address/{self.address}/weblog/configuration")

    # ── Pastebin ───────────────────────────────────────────────────────────────

    def list_pastes(self) -> list[Paste]:
        """Return all pastes (including unlisted, requires auth)."""
        response = self._request("GET", f"/address/{self.address}/pastebin")
        return [Paste.from_dict(p) for p in response.get("pastes", [])]

    def get_paste(self, title: str) -> Paste:
        """Fetch a single paste by title (public, no auth required)."""
        response = self._request("GET", f"/address/{self.address}/pastebin/{title}")
        return Paste.from_dict(response.get("paste", response))

    def create_paste(self, title: str, content: str) -> Paste:
        """Create or update a paste."""
        response = self._request(
            "POST",
            f"/address/{self.address}/pastebin/",
            json={"title": title, "content": content},
        )
        return Paste.from_dict(response)

    def delete_paste(self, title: str) -> str:
        """Permanently delete a paste. Returns the confirmation message."""
        response = self._request("DELETE", f"/address/{self.address}/pastebin/{title}")
        return response.get("message", "Deleted.")

    # ── Statuslog ─────────────────────────────────────────────────────────────

    def post_status(self, content: str, emoji: str = "✍️") -> Status:
        """Share a new status to your statuslog."""
        response = self._request(
            "POST",
            f"/address/{self.address}/statuses/",
            json={"emoji": emoji, "content": content},
        )
        return Status.from_dict(response)

    def list_statuses(self) -> list[Status]:
        """Retrieve all statuses for the address."""
        response = self._request("GET", f"/address/{self.address}/statuses/")
        return [Status.from_dict(s) for s in response.get("statuses", [])]

    # ── PURLs (Persistent URLs) ────────────────────────────────────────────────

    def list_purls(self) -> list[Purl]:
        """Return all PURLs for the address."""
        response = self._request("GET", f"/address/{self.address}/purls")
        return [Purl.from_dict(p) for p in response.get("purls", [])]

    def get_purl(self, name: str) -> Purl:
        """Fetch a single PURL by name."""
        response = self._request("GET", f"/address/{self.address}/purl/{name}")
        return Purl.from_dict(response.get("purl", response))

    def create_purl(self, name: str, url: str, listed: bool = True) -> Purl:
        """Create a new PURL (persistent redirect)."""
        response = self._request(
            "POST",
            f"/address/{self.address}/purl",
            json={"name": name, "url": url, "listed": listed},
        )
        return Purl.from_dict(response)

    def delete_purl(self, name: str) -> str:
        """Delete a PURL."""
        response = self._request("DELETE", f"/address/{self.address}/purl/{name}")
        return response.get("message", "Deleted.")

    # ── Now page ───────────────────────────────────────────────────────────────

    def get_now(self) -> NowPage:
        """Retrieve the /now page content (public, no auth required)."""
        response = self._request("GET", f"/address/{self.address}/now")
        return NowPage.from_dict(response.get("now", response))

    def update_now(self, content: str, listed: bool = True) -> NowPage:
        """Update the /now page."""
        response = self._request(
            "POST",
            f"/address/{self.address}/now",
            json={"content": content, "listed": "1" if listed else "0"},
        )
        return NowPage.from_dict(response)

    @staticmethod
    def get_now_garden() -> list[NowPage]:
        """Retrieve the Now Garden — all listed /now pages (no auth)."""
        resp = requests.get("https://api.omg.lol/now/garden")
        data = resp.json()
        return [NowPage.from_dict(n) for n in data.get("response", {}).get("garden", [])]

    # ── DNS ────────────────────────────────────────────────────────────────────

    def list_dns_records(self) -> list[DnsRecord]:
        """Return all DNS records for the address."""
        response = self._request("GET", f"/address/{self.address}/dns")
        return [DnsRecord.from_dict(r) for r in response.get("dns", [])]

    def create_dns_record(self, record_type: str, name: str, data: str, ttl: int = 3600) -> DnsRecord:
        """Create a DNS record."""
        response = self._request(
            "POST",
            f"/address/{self.address}/dns",
            json={"type": record_type, "name": name, "data": data, "ttl": ttl},
        )
        return DnsRecord.from_dict(response)

    def update_dns_record(self, record_id: str, record_type: str, name: str, data: str, ttl: int = 3600) -> DnsRecord:
        """Update an existing DNS record."""
        response = self._request(
            "PATCH",
            f"/address/{self.address}/dns/{record_id}",
            json={"type": record_type, "name": name, "data": data, "ttl": ttl},
        )
        return DnsRecord.from_dict(response)

    def delete_dns_record(self, record_id: str) -> str:
        """Delete a DNS record."""
        response = self._request("DELETE", f"/address/{self.address}/dns/{record_id}")
        return response.get("message", "Deleted.")

    # ── Profile picture ─────────────────────────────────────────────────────────

    def upload_pfp(self, filepath: str | Path) -> str:
        """Upload a profile picture. Returns the API confirmation message."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        image_data = path.read_bytes()
        response = self._request(
            "POST",
            f"/address/{self.address}/pfp",
            data=image_data,
            headers={"Content-Type": "application/octet-stream"},
        )
        return response.get("message", "Uploaded.")

    # ── Web / Profile ──────────────────────────────────────────────────────────

    def get_web(self) -> dict:
        """Retrieve the web page / profile content."""
        return self._request("GET", f"/address/{self.address}/web")

    def update_web(self, content: str, publish: bool = True) -> dict:
        """Update and optionally publish the web page / profile."""
        payload = {"content": content}
        if publish:
            payload["publish"] = True
        return self._request(
            "POST",
            f"/address/{self.address}/web",
            json=payload,
        )

    # ── Email ──────────────────────────────────────────────────────────────────

    def get_email_forwarding(self) -> dict:
        """Retrieve current email forwarding settings."""
        return self._request("GET", f"/address/{self.address}/email/")

    def set_email_forwarding(self, destination: str) -> dict:
        """Set email forwarding destination."""
        return self._request(
            "POST",
            f"/address/{self.address}/email/",
            json={"destination": destination},
        )

    # ── Account / address info ────────────────────────────────────────────────

    def get_address_info(self) -> dict:
        """Get private info about the address."""
        return self._request("GET", f"/address/{self.address}/info")

    def get_service_info(self) -> dict:
        """Get public omg.lol service stats (no auth needed)."""
        return self._request("GET", "/service/info")


# ── CLI ──────────────────────────────────────────────────────────────────────

import argparse


def _get_client() -> OmgLol:
    api_key = os.environ.get("OMGLOL_API_KEY")
    address = os.environ.get("OMGLOL_ADDRESS")
    if not api_key or not address:
        print("Error: Set OMGLOL_API_KEY and OMGLOL_ADDRESS in .env or environment")
        sys.exit(1)
    return OmgLol(api_key=api_key, address=address)


# ── Weblog commands ──────────────────────────────────────────────────────────

def cmd_post(args: argparse.Namespace) -> None:
    client = _get_client()
    for f in args.files:
        if args.dry_run:
            print(f"[dry-run] Would publish: {f}")
            continue
        try:
            client.post_markdown(f)
        except Exception as e:
            print(f"  Error publishing {f}: {e}", file=sys.stderr)


def cmd_posts_list(args: argparse.Namespace) -> None:
    client = _get_client()
    for post in client.list_posts():
        print(f"  {post.date:16s}  {post.title}  ({post.slug})")


def cmd_posts_get(args: argparse.Namespace) -> None:
    client = _get_client()
    post = client.get_post(args.entry_id)
    print(f"Title: {post.title}")
    print(f"Date:  {post.date}")
    print(f"Slug:  {post.slug}")
    print(f"URL:   {post.location}")
    print()
    print(post.body or post.source)


def cmd_posts_delete(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete post: {args.entry_id}")
        return
    client = _get_client()
    print(client.delete_post(args.entry_id))


# ── Paste commands ───────────────────────────────────────────────────────────

def cmd_paste_list(args: argparse.Namespace) -> None:
    client = _get_client()
    for paste in client.list_pastes():
        print(f"  {paste.title:30s}  {paste.modified_on}")


def cmd_paste_get(args: argparse.Namespace) -> None:
    client = _get_client()
    paste = client.get_paste(args.title)
    print(paste.content)


def cmd_paste_create(args: argparse.Namespace) -> None:
    content = args.content
    if content == "-":
        content = sys.stdin.read()
    if args.dry_run:
        print(f"[dry-run] Would create paste '{args.title}' ({len(content)} chars)")
        return
    client = _get_client()
    client.create_paste(args.title, content)
    print(f"Paste '{args.title}' created.")


def cmd_paste_delete(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete paste: {args.title}")
        return
    client = _get_client()
    print(client.delete_paste(args.title))


# ── Status commands ──────────────────────────────────────────────────────────

def cmd_status_post(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would post status: {args.emoji} {args.content}")
        return
    client = _get_client()
    client.post_status(args.content, emoji=args.emoji)
    print("Status posted.")


def cmd_status_list(args: argparse.Namespace) -> None:
    client = _get_client()
    for status in client.list_statuses():
        print(f"  {status.emoji} {status.content}  ({status.created})")


# ── PURL commands ────────────────────────────────────────────────────────────

def cmd_purl_list(args: argparse.Namespace) -> None:
    client = _get_client()
    for purl in client.list_purls():
        print(f"  {purl.name:20s} → {purl.url}")


def cmd_purl_create(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would create PURL '{args.name}' → {args.url}")
        return
    client = _get_client()
    client.create_purl(args.name, args.url, listed=not args.unlisted)
    print(f"PURL '{args.name}' → {args.url}")


def cmd_purl_delete(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete PURL: {args.name}")
        return
    client = _get_client()
    print(client.delete_purl(args.name))


# ── Now commands ─────────────────────────────────────────────────────────────

def cmd_now_get(args: argparse.Namespace) -> None:
    client = _get_client()
    now = client.get_now()
    print(now.content)


def cmd_now_update(args: argparse.Namespace) -> None:
    content = args.content
    if content == "-":
        content = sys.stdin.read()
    if args.dry_run:
        print(f"[dry-run] Would update /now page ({len(content)} chars)")
        return
    client = _get_client()
    client.update_now(content, listed=not args.unlisted)
    print("Now page updated.")


# ── DNS commands ─────────────────────────────────────────────────────────────

def cmd_dns_list(args: argparse.Namespace) -> None:
    client = _get_client()
    for rec in client.list_dns_records():
        print(f"  [{rec.id}] {rec.record_type:6s} {rec.name:30s} → {rec.data}  (TTL {rec.ttl})")


def cmd_dns_create(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would create DNS: {args.type} {args.name} → {args.data}")
        return
    client = _get_client()
    rec = client.create_dns_record(args.type, args.name, args.data, ttl=args.ttl)
    print(f"DNS record created: {rec.record_type} {rec.name} → {rec.data}")


def cmd_dns_delete(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would delete DNS record: {args.id}")
        return
    client = _get_client()
    print(client.delete_dns_record(args.id))


# ── Web commands ─────────────────────────────────────────────────────────────

def cmd_web_get(args: argparse.Namespace) -> None:
    client = _get_client()
    web = client.get_web()
    print(web.get("content", web))


def cmd_web_update(args: argparse.Namespace) -> None:
    content = args.content
    if content == "-":
        content = sys.stdin.read()
    if args.dry_run:
        print(f"[dry-run] Would update web page ({len(content)} chars, {'draft' if args.draft else 'publish'})")
        return
    client = _get_client()
    client.update_web(content, publish=not args.draft)
    print("Web page updated.")


# ── Email commands ───────────────────────────────────────────────────────────

def cmd_email_get(args: argparse.Namespace) -> None:
    client = _get_client()
    info = client.get_email_forwarding()
    print(info)


def cmd_email_set(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would set email forwarding to: {args.destination}")
        return
    client = _get_client()
    client.set_email_forwarding(args.destination)
    print(f"Email forwarding set to {args.destination}")


# ── PFP command ──────────────────────────────────────────────────────────────

def cmd_pfp_upload(args: argparse.Namespace) -> None:
    if args.dry_run:
        print(f"[dry-run] Would upload profile picture: {args.file}")
        return
    client = _get_client()
    print(client.upload_pfp(args.file))


# ── Info commands ────────────────────────────────────────────────────────────

def cmd_info(args: argparse.Namespace) -> None:
    client = _get_client()
    info = client.get_address_info()
    print(info)


# ── Parser ───────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="omglol", description="omg.lol CLI client")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be sent without making changes")
    sub = parser.add_subparsers(dest="command")

    # post (publish markdown files)
    p = sub.add_parser("post", help="Publish markdown files to weblog")
    p.add_argument("files", nargs="+", help="Markdown files to publish")
    p.set_defaults(func=cmd_post)

    # posts
    posts = sub.add_parser("posts", help="Manage weblog posts")
    posts_sub = posts.add_subparsers(dest="subcommand")

    p = posts_sub.add_parser("list", help="List all posts")
    p.set_defaults(func=cmd_posts_list)

    p = posts_sub.add_parser("get", help="Get a post by ID")
    p.add_argument("entry_id")
    p.set_defaults(func=cmd_posts_get)

    p = posts_sub.add_parser("delete", help="Delete a post")
    p.add_argument("entry_id")
    p.set_defaults(func=cmd_posts_delete)

    # paste
    paste = sub.add_parser("paste", help="Manage pastes")
    paste_sub = paste.add_subparsers(dest="subcommand")

    p = paste_sub.add_parser("list", help="List all pastes")
    p.set_defaults(func=cmd_paste_list)

    p = paste_sub.add_parser("get", help="Get a paste")
    p.add_argument("title")
    p.set_defaults(func=cmd_paste_get)

    p = paste_sub.add_parser("create", help="Create a paste (use '-' for stdin)")
    p.add_argument("title")
    p.add_argument("content")
    p.set_defaults(func=cmd_paste_create)

    p = paste_sub.add_parser("delete", help="Delete a paste")
    p.add_argument("title")
    p.set_defaults(func=cmd_paste_delete)

    # status
    status = sub.add_parser("status", help="Manage statuslog")
    status_sub = status.add_subparsers(dest="subcommand")

    p = status_sub.add_parser("post", help="Post a status")
    p.add_argument("content")
    p.add_argument("--emoji", default="✍️")
    p.set_defaults(func=cmd_status_post)

    p = status_sub.add_parser("list", help="List all statuses")
    p.set_defaults(func=cmd_status_list)

    # purl
    purl = sub.add_parser("purl", help="Manage PURLs")
    purl_sub = purl.add_subparsers(dest="subcommand")

    p = purl_sub.add_parser("list", help="List all PURLs")
    p.set_defaults(func=cmd_purl_list)

    p = purl_sub.add_parser("create", help="Create a PURL")
    p.add_argument("name")
    p.add_argument("url")
    p.add_argument("--unlisted", action="store_true")
    p.set_defaults(func=cmd_purl_create)

    p = purl_sub.add_parser("delete", help="Delete a PURL")
    p.add_argument("name")
    p.set_defaults(func=cmd_purl_delete)

    # now
    now = sub.add_parser("now", help="Manage /now page")
    now_sub = now.add_subparsers(dest="subcommand")

    p = now_sub.add_parser("get", help="Show /now page")
    p.set_defaults(func=cmd_now_get)

    p = now_sub.add_parser("update", help="Update /now page (use '-' for stdin)")
    p.add_argument("content")
    p.add_argument("--unlisted", action="store_true")
    p.set_defaults(func=cmd_now_update)

    # dns
    dns = sub.add_parser("dns", help="Manage DNS records")
    dns_sub = dns.add_subparsers(dest="subcommand")

    p = dns_sub.add_parser("list", help="List DNS records")
    p.set_defaults(func=cmd_dns_list)

    p = dns_sub.add_parser("create", help="Create a DNS record")
    p.add_argument("type", choices=["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "NS", "CAA"])
    p.add_argument("name")
    p.add_argument("data")
    p.add_argument("--ttl", type=int, default=3600)
    p.set_defaults(func=cmd_dns_create)

    p = dns_sub.add_parser("delete", help="Delete a DNS record")
    p.add_argument("id")
    p.set_defaults(func=cmd_dns_delete)

    # web
    web = sub.add_parser("web", help="Manage web page / profile")
    web_sub = web.add_subparsers(dest="subcommand")

    p = web_sub.add_parser("get", help="Show web page content")
    p.set_defaults(func=cmd_web_get)

    p = web_sub.add_parser("update", help="Update web page (use '-' for stdin)")
    p.add_argument("content")
    p.add_argument("--draft", action="store_true", help="Save as draft without publishing")
    p.set_defaults(func=cmd_web_update)

    # email
    email = sub.add_parser("email", help="Manage email forwarding")
    email_sub = email.add_subparsers(dest="subcommand")

    p = email_sub.add_parser("get", help="Show forwarding settings")
    p.set_defaults(func=cmd_email_get)

    p = email_sub.add_parser("set", help="Set forwarding destination")
    p.add_argument("destination")
    p.set_defaults(func=cmd_email_set)

    # pfp
    p = sub.add_parser("pfp", help="Upload profile picture")
    p.add_argument("file", help="Image file to upload")
    p.set_defaults(func=cmd_pfp_upload)

    # info
    p = sub.add_parser("info", help="Show address info")
    p.set_defaults(func=cmd_info)

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
