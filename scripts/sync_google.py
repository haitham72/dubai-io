"""Live Google Data Sync: Gmail & YouTube (Local OAuth Loopback).

Pulls latest emails and YouTube titles into data/sync/ for memory extraction.
Uses local loopback browser sign-in; never sends credentials or tokens to git or external APIs.
"""
from __future__ import annotations

import base64
import glob
import html
import json
import os
import re
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data" / "sync"
TOKEN_FILE = REPO_ROOT / "data" / "google_token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def find_client_secret() -> dict:
    candidates = list(REPO_ROOT.glob("client_secret*.json")) + list(REPO_ROOT.glob("*googleusercontent.com.json"))
    if not candidates:
        raise FileNotFoundError("No client_secret_*.json found in repo root.")
    path = candidates[0]
    data = json.loads(path.read_text(encoding="utf-8"))
    if "installed" in data:
        return data["installed"]
    if "web" in data:
        return data["web"]
    return data


class OAuthCallbackServer:
    def __init__(self, port: int = 8088):
        self.port = port
        self.auth_code: str | None = None
        self.error: str | None = None

    def run(self, auth_url: str) -> str:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # suppress default log output

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)

                if "code" in params:
                    parent.auth_code = params["code"][0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html_content = """
                    <html>
                    <body style="font-family:sans-serif; text-align:center; padding-top:50px;">
                        <h2 style="color:#2e7d32;">Authentication Successful!</h2>
                        <p>You can close this browser tab and return to your terminal.</p>
                    </body>
                    </html>
                    """
                    self.wfile.write(html_content.encode("utf-8"))
                elif "error" in params:
                    parent.error = params["error"][0]
                    self.send_response(400)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(f"Authentication failed: {parent.error}".encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

        server = HTTPServer(("127.0.0.1", self.port), Handler)
        print(f"\n[OAuth] Opening browser for authorization on port {self.port}...")
        webbrowser.open(auth_url)

        # Handle requests until we capture code or error
        while not self.auth_code and not self.error:
            server.handle_request()

        server.server_close()

        if self.error:
            raise RuntimeError(f"OAuth authorization failed: {self.error}")
        if not self.auth_code:
            raise RuntimeError("OAuth code was not received.")
        return self.auth_code


def get_tokens(creds: dict) -> dict:
    if TOKEN_FILE.exists():
        tokens = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        if tokens.get("access_token"):
            # Check if token needs refresh or is still usable
            # Try a lightweight check
            with httpx.Client() as client:
                res = client.get(
                    "https://www.googleapis.com/oauth2/v1/tokeninfo",
                    params={"access_token": tokens["access_token"]},
                )
                if res.status_code == 200:
                    return tokens
                if tokens.get("refresh_token"):
                    # Refresh token
                    print("[OAuth] Access token expired, refreshing...")
                    refresh_res = client.post(
                        creds.get("token_uri", "https://oauth2.googleapis.com/token"),
                        data={
                            "client_id": creds["client_id"],
                            "client_secret": creds["client_secret"],
                            "refresh_token": tokens["refresh_token"],
                            "grant_type": "refresh_token",
                        },
                    )
                    if refresh_res.status_code == 200:
                        new_data = refresh_res.json()
                        tokens["access_token"] = new_data["access_token"]
                        TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
                        return tokens

    # Start new authorization flow
    redirect_uri = "http://localhost:8088/"
    auth_params = {
        "client_id": creds["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{creds.get('auth_uri', 'https://accounts.google.com/o/oauth2/auth')}?{urllib.parse.urlencode(auth_params)}"

    runner = OAuthCallbackServer(port=8088)
    code = runner.run(auth_url)

    # Exchange code for tokens
    with httpx.Client() as client:
        token_res = client.post(
            creds.get("token_uri", "https://oauth2.googleapis.com/token"),
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        if token_res.status_code != 200:
            raise RuntimeError(f"Failed to exchange token: {token_res.status_code} {token_res.text}")
        tokens = token_res.json()
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
        print("[OAuth] Tokens saved successfully to data/google_token.json")
        return tokens


def fetch_gmail(
    tokens: dict,
    max_tokens: int = 50000,
    days: int | None = 30,
    since_date: str | None = None,
    until_date: str | None = None,
    primary_only: bool = True,
) -> list[dict]:
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    
    # Construct exact Gmail search query constraints
    query_parts = ["-in:trash", "-in:spam"]
    if primary_only:
        query_parts.append("category:primary")
    if since_date and until_date:
        query_parts.append(f"after:{since_date.replace('-', '/')} before:{until_date.replace('-', '/')}")
    elif days:
        query_parts.append(f"newer_than:{days}d")
    
    q_str = " ".join(query_parts)
    print(f"\n[Gmail] Query: '{q_str}'")
    print(f"[Gmail] Token Budget Cap: ~{max_tokens:,} tokens (~{int(max_tokens * 2.2):,} characters)")
    
    with httpx.Client(timeout=30.0) as client:
        # 1. Search messages matching constraints
        list_res = client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers=headers,
            params={"q": q_str, "maxResults": 250},
        )
        if list_res.status_code != 200:
            raise RuntimeError(f"Gmail search failed: {list_res.status_code} {list_res.text}")
        
        msg_items = list_res.json().get("messages", [])
        print(f"[Gmail] Matching messages found: {len(msg_items)}")

        results = []
        cumulative_tokens = 0
        
        for i, item in enumerate(msg_items):
            if cumulative_tokens >= max_tokens:
                print(f"[Gmail] Reached token budget limit ({cumulative_tokens:,} >= {max_tokens:,} tokens). Stopping download.")
                break

            msg_id = item["id"]
            m_res = client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}",
                headers=headers,
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
            )
            if m_res.status_code != 200:
                continue
            m_data = m_res.json()
            payload = m_data.get("payload") or {}
            hdr_list = payload.get("headers") or []

            def get_header(name: str) -> str:
                for h in hdr_list:
                    if h.get("name", "").lower() == name.lower():
                        return h.get("value", "")
                return ""

            subject = get_header("Subject") or "(no subject)"
            sender = get_header("From")
            date_str = get_header("Date")
            snippet = html.unescape(m_data.get("snippet") or "")
            
            # Estimate tokens using the repo's lab convention (chars / 2.2)
            est_msg_tokens = int((len(subject) + len(sender) + len(snippet)) / 2.2) + 10
            cumulative_tokens += est_msg_tokens

            results.append({
                "id": msg_id,
                "thread_id": m_data.get("threadId"),
                "date": date_str,
                "from": sender,
                "subject": subject,
                "snippet": snippet,
                "internal_date": m_data.get("internalDate"),
                "est_tokens": est_msg_tokens,
            })
            
            if (i + 1) % 15 == 0 or (i + 1) == len(msg_items):
                print(f"  Processed {i + 1} emails | Cumulative tokens: ~{cumulative_tokens:,}/{max_tokens:,}")

    out_file = DATA_DIR / "gmail_latest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Gmail] Saved {len(results)} emails (~{cumulative_tokens:,} tokens) to {out_file}")
    return results


def fetch_youtube(tokens: dict) -> list[dict]:
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    print("\n[YouTube] Fetching channel details and titles...")
    results = []
    with httpx.Client(timeout=30.0) as client:
        # 1. Get channel & uploads playlist
        ch_res = client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            headers=headers,
            params={"part": "snippet,contentDetails", "mine": "true"},
        )
        if ch_res.status_code == 200:
            ch_data = ch_res.json()
            items = ch_data.get("items") or []
            if items:
                channel = items[0]
                ch_title = (channel.get("snippet") or {}).get("title")
                uploads_id = ((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
                print(f"[YouTube] Connected to channel: '{ch_title}'")

                if uploads_id:
                    p_res = client.get(
                        "https://www.googleapis.com/youtube/v3/playlistItems",
                        headers=headers,
                        params={"part": "snippet", "playlistId": uploads_id, "maxResults": 50},
                    )
                    if p_res.status_code == 200:
                        for entry in p_res.json().get("items", []):
                            snip = entry.get("snippet") or {}
                            results.append({
                                "title": snip.get("title"),
                                "published_at": snip.get("publishedAt"),
                                "video_id": (snip.get("resourceId") or {}).get("videoId"),
                                "type": "upload",
                                "channel": snip.get("channelTitle"),
                            })

        # 2. Try Liked Videos playlist (playlistId=LL)
        liked_res = client.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            headers=headers,
            params={"part": "snippet", "playlistId": "LL", "maxResults": 50},
        )
        if liked_res.status_code == 200:
            liked_count = 0
            for entry in liked_res.json().get("items", []):
                snip = entry.get("snippet") or {}
                results.append({
                    "title": snip.get("title"),
                    "published_at": snip.get("publishedAt"),
                    "video_id": (snip.get("resourceId") or {}).get("videoId"),
                    "type": "liked_video",
                    "channel": snip.get("videoOwnerChannelTitle") or snip.get("channelTitle"),
                })
                liked_count += 1
            print(f"[YouTube] Fetched {liked_count} liked video titles.")

    out_file = DATA_DIR / "youtube_latest.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[YouTube] Saved {len(results)} items to {out_file}")
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Live Google Data Sync: Gmail & YouTube")
    parser.add_argument("--tokens", type=int, default=50000, help="Token budget ceiling (default: 50,000)")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default: 30)")
    parser.add_argument("--since", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--until", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--all-categories", action="store_true", help="Include promotions/social/updates")
    args = parser.parse_args()

    print("=" * 60)
    print("Live Google Data Sync: Gmail & YouTube")
    print(f"Constraints: ~{args.tokens:,} tokens cap | "
          f"{f'{args.since} to {args.until}' if args.since else f'Last {args.days} days'} | "
          f"{'All categories' if args.all_categories else 'Category: Primary'}")
    print("=" * 60)
    creds = find_client_secret()
    tokens = get_tokens(creds)
    gmail_data = fetch_gmail(
        tokens,
        max_tokens=args.tokens,
        days=args.days,
        since_date=args.since,
        until_date=args.until,
        primary_only=not args.all_categories,
    )
    youtube_data = fetch_youtube(tokens)
    print("\n[Done] Sync completed successfully!")
    print(f"Total Emails:   {len(gmail_data)}")
    print(f"Total YouTube:  {len(youtube_data)}")


if __name__ == "__main__":
    main()
