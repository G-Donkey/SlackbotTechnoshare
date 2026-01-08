#!/usr/bin/env python3
"""
Utility: print Slack messages our system would read.

Usage:
  python scripts/print_slack_input.py --channel C12345 --limit 10 --parse

This script uses the project's `slack_client` wrapper to fetch recent messages
and prints them. If `--parse` is provided and `technoshare_commentator.slack.parse`
exists, it will also show parsed snippets.

Requires: SLACK_BOT_TOKEN in environment (same as the main app).
"""
from __future__ import annotations
import argparse
import os
import json
import sys
from typing import Any

# Add project src to path if not already available
ROOT = os.path.dirname(os.path.dirname(__file__))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from technoshare_commentator.slack.client import slack_client


def fetch_messages(channel: str, limit: int = 10) -> Any:
    try:
        msgs = slack_client.get_latest_messages(channel, limit=limit)
        return msgs
    except Exception as e:
        print(f"Error fetching messages: {e}")
        raise


def pretty_print_messages(messages: list[dict[str, Any]]):
    for m in messages:
        ts = m.get("ts")
        user = m.get("user") or m.get("username") or m.get("bot_id")
        text = m.get("text")
        attachments = m.get("attachments")
        blocks = m.get("blocks")
        print("---")
        print(f"ts: {ts}")
        print(f"user: {user}")
        print("text:")
        print(text)
        if attachments:
            print("attachments:")
            print(json.dumps(attachments, indent=2))
        if blocks:
            print("blocks:")
            print(json.dumps(blocks, indent=2))


def try_parse_messages(messages: list[dict[str, Any]]):
    try:
        from technoshare_commentator.slack.parse import parse_messages_to_snippets
    except Exception:
        print("No parser available at technoshare_commentator.slack.parse")
        return

    snippets = parse_messages_to_snippets(messages)
    print("\nParsed snippets:")
    print(json.dumps(snippets, indent=2))


def main():
    p = argparse.ArgumentParser(description="Print Slack messages fetched by our bot")
    p.add_argument("--channel", required=True, help="Channel ID to read from (e.g., C12345)")
    p.add_argument("--limit", type=int, default=10, help="Number of messages to fetch")
    p.add_argument("--parse", action="store_true", help="Attempt to parse messages into snippets")
    args = p.parse_args()

    print(f"Fetching last {args.limit} messages from channel {args.channel}...\n")
    msgs = fetch_messages(args.channel, limit=args.limit)
    pretty_print_messages(msgs)

    if args.parse:
        try:
            try_parse_messages(msgs)
        except Exception as e:
            print(f"Parser error: {e}")


if __name__ == '__main__':
    main()
