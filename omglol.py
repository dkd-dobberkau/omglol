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
    for entry in client.list_posts():
        print(entry["title"], entry["location"])
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


class OmgLolError(Exception):
    pass


class OmgLol:
    BASE_URL = "https://api.omg.lol"

    def __init__(self, api_key: str, address: str):
        self.address = address
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs):
        url = f"{self.BASE_URL}{path}"
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("request", {}).get("success", True):
            raise OmgLolError(data.get("response", {}).get("message", "Unknown error"))
        return data.get("response", data)

    # ── Weblog ────────────────────────────────────────────────────────────────

    def list_posts(self) -> list[dict]:
        """Return all weblog entries."""
        response = self._request("GET", f"/address/{self.address}/weblog/entries")
        return response.get("entries", [])

    def get_post(self, entry_id: str) -> dict:
        """Fetch a single weblog entry by ID."""
        response = self._request("GET", f"/address/{self.address}/weblog/entry/{entry_id}")
        return response.get("entry", response)

    def get_latest_post(self) -> dict:
        """Fetch the latest published post (no auth required)."""
        response = self._request("GET", f"/address/{self.address}/weblog/post/latest")
        return response.get("post", response)

    def create_post(
        self,
        title: str,
        content: str,
        date: datetime | None = None,
        slug: str | None = None,
        entry_id: str | None = None,
    ) -> dict:
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
            data=source,
            headers={"Content-Type": "text/plain"},
        )
        return response.get("entry", response)

    def post_markdown(self, filepath: str | Path, entry_id: str | None = None) -> dict:
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
            The API response dict for the created/updated entry.
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
        print(f"  Published at: https://{self.address}.weblog.lol{result.get('location', '')}")
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

    def list_pastes(self) -> list[dict]:
        """Return all pastes (including unlisted, requires auth)."""
        response = self._request("GET", f"/address/{self.address}/pastebin")
        return response.get("pastes", [])

    def get_paste(self, title: str) -> dict:
        """Fetch a single paste by title (public, no auth required)."""
        response = self._request("GET", f"/address/{self.address}/pastebin/{title}")
        return response.get("paste", response)

    def create_paste(self, title: str, content: str) -> dict:
        """Create or update a paste."""
        response = self._request(
            "POST",
            f"/address/{self.address}/pastebin/",
            json={"title": title, "content": content},
        )
        return response

    def delete_paste(self, title: str) -> str:
        """Permanently delete a paste. Returns the confirmation message."""
        response = self._request("DELETE", f"/address/{self.address}/pastebin/{title}")
        return response.get("message", "Deleted.")

    # ── Statuslog ─────────────────────────────────────────────────────────────

    def post_status(self, content: str, emoji: str = "✍️") -> dict:
        """Share a new status to your statuslog."""
        response = self._request(
            "POST",
            f"/address/{self.address}/statuses/",
            json={"emoji": emoji, "content": content},
        )
        return response

    def list_statuses(self) -> list[dict]:
        """Retrieve all statuses for the address."""
        response = self._request("GET", f"/address/{self.address}/statuses/")
        return response.get("statuses", [])

    # ── PURLs (Persistent URLs) ────────────────────────────────────────────────

    def list_purls(self) -> list[dict]:
        """Return all PURLs for the address."""
        response = self._request("GET", f"/address/{self.address}/purls")
        return response.get("purls", [])

    def get_purl(self, name: str) -> dict:
        """Fetch a single PURL by name."""
        response = self._request("GET", f"/address/{self.address}/purl/{name}")
        return response.get("purl", response)

    def create_purl(self, name: str, url: str, listed: bool = True) -> dict:
        """Create a new PURL (persistent redirect)."""
        return self._request(
            "POST",
            f"/address/{self.address}/purl",
            json={"name": name, "url": url, "listed": listed},
        )

    def delete_purl(self, name: str) -> str:
        """Delete a PURL."""
        response = self._request("DELETE", f"/address/{self.address}/purl/{name}")
        return response.get("message", "Deleted.")

    # ── Now page ───────────────────────────────────────────────────────────────

    def get_now(self) -> dict:
        """Retrieve the /now page content (public, no auth required)."""
        return self._request("GET", f"/address/{self.address}/now")

    def update_now(self, content: str, listed: bool = True) -> dict:
        """Update the /now page."""
        return self._request(
            "POST",
            f"/address/{self.address}/now",
            json={"content": content, "listed": "1" if listed else "0"},
        )

    @staticmethod
    def get_now_garden() -> list[dict]:
        """Retrieve the Now Garden — all listed /now pages (no auth)."""
        resp = requests.get("https://api.omg.lol/now/garden")
        data = resp.json()
        return data.get("response", {}).get("garden", [])

    # ── DNS ────────────────────────────────────────────────────────────────────

    def list_dns_records(self) -> list[dict]:
        """Return all DNS records for the address."""
        response = self._request("GET", f"/address/{self.address}/dns")
        return response.get("dns", [])

    def create_dns_record(self, record_type: str, name: str, data: str, ttl: int = 3600) -> dict:
        """Create a DNS record."""
        return self._request(
            "POST",
            f"/address/{self.address}/dns",
            json={"type": record_type, "name": name, "data": data, "ttl": ttl},
        )

    def update_dns_record(self, record_id: str, record_type: str, name: str, data: str, ttl: int = 3600) -> dict:
        """Update an existing DNS record."""
        return self._request(
            "PATCH",
            f"/address/{self.address}/dns/{record_id}",
            json={"type": record_type, "name": name, "data": data, "ttl": ttl},
        )

    def delete_dns_record(self, record_id: str) -> str:
        """Delete a DNS record."""
        response = self._request("DELETE", f"/address/{self.address}/dns/{record_id}")
        return response.get("message", "Deleted.")

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


# ── CLI convenience ───────────────────────────────────────────────────────────

def main():
    """
    Minimal CLI: publish one or more markdown files.

    Usage:
        python omglol.py <api_key> <address> post.md [post2.md ...]
    """
    if len(sys.argv) < 2:
        print("Usage: python omglol.py <file.md> [file2.md ...]")
        sys.exit(1)

    api_key = os.environ.get("OMGLOL_API_KEY")
    address = os.environ.get("OMGLOL_ADDRESS")

    if not api_key or not address:
        print("Error: Set OMGLOL_API_KEY and OMGLOL_ADDRESS in .env or environment")
        sys.exit(1)

    files = sys.argv[1:]

    client = OmgLol(api_key=api_key, address=address)

    for f in files:
        try:
            client.post_markdown(f)
        except Exception as e:
            print(f"  Error publishing {f}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
