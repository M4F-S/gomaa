"""Mnemosyne CLI — command-line interface for the memory engine."""

import argparse
import json
import sys
import os

from mnemosyne.core import UnifiedMemorySystem


def get_memory():
    """Create a UnifiedMemorySystem from environment or defaults."""
    return UnifiedMemorySystem()


def cmd_remember(args):
    """Store a memory."""
    mem = get_memory()
    result = mem.remember(
        title=args.title,
        content=args.content,
        tags=args.tags.split(",") if args.tags else [],
        wing=args.wing,
        room=args.room,
        salience=args.salience,
    )
    print(json.dumps(result, indent=2, default=str))


def cmd_recall(args):
    """Search memories."""
    mem = get_memory()
    results = mem.recall(
        query=args.query,
        mode=args.mode,
        top_k=args.top_k,
        scope={"wing": args.wing} if args.wing else None,
    )
    for r in results:
        wing_val = r.get('wing', '?')
        room_val = r.get('room', '?')
        title_val = r.get('title', '?')
        print(f"  [{wing_val}/{room_val}] {title_val}")
        content_preview = (r.get("content", "") or "")[:120]
        print(f"    {content_preview}...")
        print()


def cmd_timeline(args):
    """Show recent memory activity."""
    mem = get_memory()
    entries = mem.timeline(limit=args.limit)
    for e in entries:
        ts = e.get('created_at', '?')
        op = e.get('operation', '?')
        title = e.get('title', '?')
        print(f"  {ts}  {op}  {title}")


def cmd_stats(args):
    """Show memory system statistics."""
    mem = get_memory()
    stats = mem.stats()
    print(json.dumps(stats, indent=2, default=str))


def cmd_consolidate(args):
    """Run nightly consolidation: temporal decay + archive stale memories."""
    mem = get_memory()
    if hasattr(mem.db, "apply_decay"):
        result = mem.db.apply_decay(
            decay_rate=args.decay_rate,
            archive_threshold=args.threshold,
        )
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Temporal decay requires PostgreSQL (not available with SQLite fallback).")
        sys.exit(1)


def cmd_server(args):
    """Run MCP server."""
    from mnemosyne.mcp_server import MCPServer
    server = MCPServer()
    server.run()


def main():
    parser = argparse.ArgumentParser(
        prog="mnemosyne",
        description="Mnemosyne - Local-first memory engine for AI agents",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # remember
    p_rem = sub.add_parser("remember", help="Store a memory")
    p_rem.add_argument("title", help="Memory title")
    p_rem.add_argument("content", help="Memory content")
    p_rem.add_argument("--tags", default="", help="Comma-separated tags")
    p_rem.add_argument("--wing", default="general", help="Domain/project wing")
    p_rem.add_argument("--room", default="general", help="Topic room")
    p_rem.add_argument("--salience", type=float, default=0.5, help="Salience score 0-1")
    p_rem.set_defaults(func=cmd_remember)

    # recall
    p_rec = sub.add_parser("recall", help="Search memories")
    p_rec.add_argument("query", help="Search query")
    p_rec.add_argument("--mode", default="hybrid", choices=["hybrid", "semantic", "keyword", "graph"])
    p_rec.add_argument("--top-k", type=int, default=5, dest="top_k")
    p_rec.add_argument("--wing", default=None, help="Restrict to wing")
    p_rec.set_defaults(func=cmd_recall)

    # timeline
    p_tl = sub.add_parser("timeline", help="Show recent activity")
    p_tl.add_argument("--limit", type=int, default=20)
    p_tl.set_defaults(func=cmd_timeline)

    # stats
    p_st = sub.add_parser("stats", help="Show system statistics")
    p_st.set_defaults(func=cmd_stats)

    # consolidate
    p_con = sub.add_parser("consolidate", help="Run temporal decay and archive stale memories")
    p_con.add_argument("--decay-rate", type=float, default=0.95, dest="decay_rate")
    p_con.add_argument("--threshold", type=float, default=0.05, help="Archive below this salience")
    p_con.set_defaults(func=cmd_consolidate)

    # server
    p_srv = sub.add_parser("server", help="Run MCP server (stdio)")
    p_srv.set_defaults(func=cmd_server)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
