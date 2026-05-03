"""
Reddit research tools — no API key required.

Appending .json to any Reddit URL returns structured data.
We use this to give agents real, unfiltered market intelligence.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "claude-crew/1.0 (market research tool)"}
TIMEOUT = 12


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def reddit_search(query: str, subreddit: str = "", sort: str = "relevance", limit: int = 8) -> str:
    """Search Reddit and return a formatted summary of top posts."""
    params = urllib.parse.urlencode({
        "q": query,
        "sort": sort,
        "limit": limit,
        "restrict_sr": "1" if subreddit else "0",
    })

    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json?{params}"
    else:
        url = f"https://www.reddit.com/search.json?{params}"

    try:
        data = _fetch(url)
    except urllib.error.HTTPError as e:
        return f"Reddit search failed: HTTP {e.code}"
    except Exception as e:
        return f"Reddit search failed: {e}"

    posts = data.get("data", {}).get("children", [])
    if not posts:
        return f"No Reddit results found for '{query}'."

    lines = [f"Reddit search results for: \"{query}\"\n"]
    for i, post in enumerate(posts, 1):
        p = post["data"]
        title = p.get("title", "")
        sub = p.get("subreddit", "")
        score = p.get("score", 0)
        comments = p.get("num_comments", 0)
        permalink = p.get("permalink", "")
        selftext = p.get("selftext", "").strip()
        preview = selftext[:250].replace("\n", " ") + ("..." if len(selftext) > 250 else "")

        lines.append(f"{i}. [{sub}] {title}")
        lines.append(f"   Score: {score:,}  |  Comments: {comments:,}")
        lines.append(f"   URL: https://reddit.com{permalink}")
        if preview:
            lines.append(f"   Preview: {preview}")
        lines.append("")

    return "\n".join(lines)


def reddit_get_comments(post_url: str, limit: int = 15) -> str:
    """
    Fetch top comments from a Reddit post.
    post_url can be a full reddit.com URL or just the /r/sub/comments/... path.
    """
    # Normalise to a path
    if post_url.startswith("http"):
        parsed = urllib.parse.urlparse(post_url)
        path = parsed.path.rstrip("/")
    else:
        path = post_url.rstrip("/")

    url = f"https://www.reddit.com{path}.json?limit={limit}&sort=top"

    try:
        data = _fetch(url)
    except urllib.error.HTTPError as e:
        return f"Failed to fetch post: HTTP {e.code}"
    except Exception as e:
        return f"Failed to fetch post: {e}"

    if not isinstance(data, list) or len(data) < 2:
        return "Could not parse Reddit post data."

    # Post metadata
    post_data = data[0]["data"]["children"][0]["data"]
    title = post_data.get("title", "")
    selftext = post_data.get("selftext", "").strip()
    score = post_data.get("score", 0)
    sub = post_data.get("subreddit", "")

    lines = [f"[r/{sub}] {title}"]
    lines.append(f"Score: {score:,}\n")
    if selftext:
        lines.append(f"Post body:\n{selftext[:500]}{'...' if len(selftext) > 500 else ''}\n")

    # Top-level comments
    comments = data[1]["data"]["children"]
    lines.append(f"Top {min(limit, len(comments))} comments:\n")
    for i, comment in enumerate(comments[:limit], 1):
        if comment.get("kind") != "t1":
            continue
        c = comment["data"]
        body = c.get("body", "").strip().replace("\n", " ")
        cscore = c.get("score", 0)
        preview = body[:300] + ("..." if len(body) > 300 else "")
        lines.append(f"{i}. (score: {cscore:,}) {preview}")

    return "\n".join(lines)


# ── Tool definitions for Claude API ────────────────────────────────────────

REDDIT_TOOLS = [
    {
        "name": "reddit_search",
        "description": (
            "Search Reddit for real user discussions about any topic. "
            "Invaluable for market research, understanding pain points, discovering "
            "competitor sentiment, and finding the language your target audience uses. "
            "Returns post titles, scores, comment counts, and previews."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'best productivity apps for developers')",
                },
                "subreddit": {
                    "type": "string",
                    "description": "Limit search to a specific subreddit (e.g. 'entrepreneur', 'SideProject', 'webdev'). Leave empty to search all of Reddit.",
                },
                "sort": {
                    "type": "string",
                    "enum": ["relevance", "hot", "new", "top"],
                    "description": "Sort order. 'top' or 'relevance' best for research.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "reddit_get_comments",
        "description": (
            "Fetch the top comments from a specific Reddit post. "
            "Use this after reddit_search to dive deep into a promising thread "
            "and extract detailed user opinions, pain points, or feature requests."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "post_url": {
                    "type": "string",
                    "description": "Full Reddit post URL or path (e.g. https://reddit.com/r/entrepreneur/comments/abc123/title/)",
                },
            },
            "required": ["post_url"],
        },
    },
]


def execute(name: str, inputs: dict) -> str:
    if name == "reddit_search":
        return reddit_search(
            query=inputs["query"],
            subreddit=inputs.get("subreddit", ""),
            sort=inputs.get("sort", "relevance"),
        )
    if name == "reddit_get_comments":
        return reddit_get_comments(post_url=inputs["post_url"])
    return f"Unknown Reddit tool: {name}"
