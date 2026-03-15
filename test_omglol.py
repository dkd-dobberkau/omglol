"""Tests for the omg.lol API client."""

import responses
import pytest
from omglol import OmgLol, OmgLolError, Post, Paste, Status, Purl, DnsRecord, NowPage


API = "https://api.omg.lol"
ADDR = "testuser"


@pytest.fixture
def client():
    return OmgLol(api_key="test-key", address=ADDR)


def _ok(data: dict) -> dict:
    """Wrap data in the omg.lol success envelope."""
    return {"request": {"success": True}, "response": data}


# ── Weblog ───────────────────────────────────────────────────────────────────


@responses.activate
def test_list_posts(client):
    responses.get(
        f"{API}/address/{ADDR}/weblog/entries",
        json=_ok({"entries": [
            {"title": "Hello", "slug": "hello", "date": "2025-03-14", "location": "/hello"},
            {"title": "World", "slug": "world", "date": "2025-03-15", "location": "/world"},
        ]}),
    )
    posts = client.list_posts()
    assert len(posts) == 2
    assert isinstance(posts[0], Post)
    assert posts[0].title == "Hello"
    assert posts[1].slug == "world"


@responses.activate
def test_get_post(client):
    responses.get(
        f"{API}/address/{ADDR}/weblog/entry/hello",
        json=_ok({"entry": {"title": "Hello", "slug": "hello", "body": "content"}}),
    )
    post = client.get_post("hello")
    assert isinstance(post, Post)
    assert post.title == "Hello"
    assert post.body == "content"


@responses.activate
def test_create_post(client):
    responses.post(
        f"{API}/address/{ADDR}/weblog/entry/hello-world",
        json=_ok({"entry": {"title": "Hello World", "slug": "hello-world", "location": "/hello-world"}}),
    )
    post = client.create_post(title="Hello World", content="Body text")
    assert isinstance(post, Post)
    assert post.slug == "hello-world"
    body = responses.calls[0].request.body
    assert "---" in body
    assert "Date:" in body
    assert "# Hello World" in body


@responses.activate
def test_delete_post(client):
    responses.delete(
        f"{API}/address/{ADDR}/weblog/delete/hello",
        json=_ok({"message": "Entry deleted."}),
    )
    msg = client.delete_post("hello")
    assert msg == "Entry deleted."


# ── Pastebin ─────────────────────────────────────────────────────────────────


@responses.activate
def test_list_pastes(client):
    responses.get(
        f"{API}/address/{ADDR}/pastebin",
        json=_ok({"pastes": [{"title": "note", "content": "stuff", "modified_on": "2025-03-14"}]}),
    )
    pastes = client.list_pastes()
    assert len(pastes) == 1
    assert isinstance(pastes[0], Paste)
    assert pastes[0].title == "note"


@responses.activate
def test_create_paste(client):
    responses.post(
        f"{API}/address/{ADDR}/pastebin/",
        json=_ok({"title": "my-paste", "content": "data"}),
    )
    paste = client.create_paste("my-paste", "data")
    assert isinstance(paste, Paste)


@responses.activate
def test_delete_paste(client):
    responses.delete(
        f"{API}/address/{ADDR}/pastebin/note",
        json=_ok({"message": "Deleted."}),
    )
    assert client.delete_paste("note") == "Deleted."


# ── Statuslog ────────────────────────────────────────────────────────────────


@responses.activate
def test_post_status(client):
    responses.post(
        f"{API}/address/{ADDR}/statuses/",
        json=_ok({"id": "123", "emoji": "🎉", "content": "Hello!", "created": "2025-03-14"}),
    )
    status = client.post_status("Hello!", emoji="🎉")
    assert isinstance(status, Status)
    assert status.content == "Hello!"


@responses.activate
def test_list_statuses(client):
    responses.get(
        f"{API}/address/{ADDR}/statuses/",
        json=_ok({"statuses": [{"id": "1", "emoji": "✍️", "content": "hi", "created": "2025-03-14"}]}),
    )
    statuses = client.list_statuses()
    assert len(statuses) == 1
    assert isinstance(statuses[0], Status)


# ── PURLs ────────────────────────────────────────────────────────────────────


@responses.activate
def test_list_purls(client):
    responses.get(
        f"{API}/address/{ADDR}/purls",
        json=_ok({"purls": [{"name": "gh", "url": "https://github.com", "listed": True}]}),
    )
    purls = client.list_purls()
    assert len(purls) == 1
    assert isinstance(purls[0], Purl)
    assert purls[0].name == "gh"


@responses.activate
def test_create_purl(client):
    responses.post(
        f"{API}/address/{ADDR}/purl",
        json=_ok({"name": "gh", "url": "https://github.com"}),
    )
    purl = client.create_purl("gh", "https://github.com")
    assert isinstance(purl, Purl)


@responses.activate
def test_delete_purl(client):
    responses.delete(
        f"{API}/address/{ADDR}/purl/gh",
        json=_ok({"message": "Deleted."}),
    )
    assert client.delete_purl("gh") == "Deleted."


# ── Now page ─────────────────────────────────────────────────────────────────


@responses.activate
def test_get_now(client):
    responses.get(
        f"{API}/address/{ADDR}/now",
        json=_ok({"now": {"content": "Working on stuff", "listed": True, "updated": "2025-03-14"}}),
    )
    now = client.get_now()
    assert isinstance(now, NowPage)
    assert now.content == "Working on stuff"


@responses.activate
def test_update_now(client):
    responses.post(
        f"{API}/address/{ADDR}/now",
        json=_ok({"content": "New content", "listed": True}),
    )
    now = client.update_now("New content")
    assert isinstance(now, NowPage)


# ── DNS ──────────────────────────────────────────────────────────────────────


@responses.activate
def test_list_dns_records(client):
    responses.get(
        f"{API}/address/{ADDR}/dns",
        json=_ok({"dns": [{"id": "1", "type": "A", "name": "@", "data": "1.2.3.4", "ttl": 3600}]}),
    )
    records = client.list_dns_records()
    assert len(records) == 1
    assert isinstance(records[0], DnsRecord)
    assert records[0].record_type == "A"


@responses.activate
def test_create_dns_record(client):
    responses.post(
        f"{API}/address/{ADDR}/dns",
        json=_ok({"id": "2", "type": "CNAME", "name": "www", "data": "example.com", "ttl": 3600}),
    )
    rec = client.create_dns_record("CNAME", "www", "example.com")
    assert isinstance(rec, DnsRecord)
    assert rec.record_type == "CNAME"


# ── Web / Profile ────────────────────────────────────────────────────────────


@responses.activate
def test_get_web(client):
    responses.get(
        f"{API}/address/{ADDR}/web",
        json=_ok({"content": "<h1>My page</h1>"}),
    )
    web = client.get_web()
    assert "content" in web or isinstance(web, dict)


# ── Email ────────────────────────────────────────────────────────────────────


@responses.activate
def test_get_email_forwarding(client):
    responses.get(
        f"{API}/address/{ADDR}/email/",
        json=_ok({"destination": "me@example.com"}),
    )
    info = client.get_email_forwarding()
    assert info.get("destination") == "me@example.com"


@responses.activate
def test_set_email_forwarding(client):
    responses.post(
        f"{API}/address/{ADDR}/email/",
        json=_ok({"message": "Forwarding updated."}),
    )
    result = client.set_email_forwarding("new@example.com")
    assert isinstance(result, dict)


# ── Error handling ───────────────────────────────────────────────────────────


@responses.activate
def test_api_error_raises(client):
    responses.get(
        f"{API}/address/{ADDR}/weblog/entries",
        json={"request": {"success": False}, "response": {"message": "Not found"}},
    )
    with pytest.raises(OmgLolError, match="Not found"):
        client.list_posts()


@responses.activate
def test_retry_on_429(client):
    # First call returns 429, second succeeds
    responses.get(
        f"{API}/address/{ADDR}/weblog/entries",
        json={"message": "rate limited"},
        status=429,
        headers={"Retry-After": "0"},
    )
    responses.get(
        f"{API}/address/{ADDR}/weblog/entries",
        json=_ok({"entries": []}),
    )
    posts = client.list_posts()
    assert posts == []
    assert len(responses.calls) == 2


# ── Auth header ──────────────────────────────────────────────────────────────


@responses.activate
def test_auth_header(client):
    responses.get(
        f"{API}/service/info",
        json=_ok({"members": 42}),
    )
    client.get_service_info()
    assert responses.calls[0].request.headers["Authorization"] == "Bearer test-key"
