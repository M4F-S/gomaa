"""
Mnemosyne CLI Interface (v3.2)
"""

import argparse
import json
import os
import sys

from mnemosyne import UnifiedMemorySystem
from mnemosyne.mcp_server import MCPServer


def main():
    parser = argparse.ArgumentParser(
        prog="mnemosyne",
        description="Mnemosyne: Local Hierarchical Memory Engine for AI Agents",
    )
    parser.add_argument("--vault-path", default=None, help="Path to Obsidian vault")
    parser.add_argument("--dsn", default=None, help="PostgreSQL connection string")
    parser.add_argument("--shared-dsn", default=None, help="Shared PostgreSQL fleet connection string")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # remember
    p_remember = subparsers.add_parser("remember", help="Store a memory note")
    p_remember.add_argument("title", help="Note title")
    p_remember.add_argument("content", help="Note markdown content")
    p_remember.add_argument("--tags", nargs="*", default=[], help="Tags list")
    p_remember.add_argument("--salience", type=float, default=0.5, help="Salience 0.0-1.0")
    p_remember.add_argument("--wing", default="general", help="Domain wing")
    p_remember.add_argument("--room", default="general", help="Topic room")
    p_remember.add_argument("--pinned", action="store_true", help="Make note permanent and immune to decay")

    # publish-shared
    p_pub = subparsers.add_parser("publish-shared", help="Publish a curated note to shared fleet memory")
    p_pub.add_argument("title", help="Note title")
    p_pub.add_argument("content", help="Note markdown content")
    p_pub.add_argument("--tags", nargs="*", default=[], help="Tags list")
    p_pub.add_argument("--wing", default="shared", help="Domain wing")
    p_pub.add_argument("--room", default="general", help="Topic room")

    # recall
    p_recall = subparsers.add_parser("recall", help="Search memory")
    p_recall.add_argument("query", help="Search query")
    p_recall.add_argument("--mode", choices=["hybrid", "semantic", "keyword", "graph"], default="hybrid")
    p_recall.add_argument("--top-k", type=int, default=5, help="Number of results")
    p_recall.add_argument("--wing", default=None, help="Filter by wing")
    p_recall.add_argument("--room", default=None, help="Filter by room")

    # timeline
    p_timeline = subparsers.add_parser("timeline", help="View memory activity timeline")
    p_timeline.add_argument("--limit", type=int, default=20, help="Number of events")

    # stats
    subparsers.add_parser("stats", help="Get memory store statistics")

    # consolidate
    p_consolidate = subparsers.add_parser("consolidate", help="Apply link reconciliation and temporal decay")
    p_consolidate.add_argument("--decay-rate", type=float, default=0.95, help="Daily retention factor")
    p_consolidate.add_argument("--archive-threshold", type=float, default=0.05, help="Salience threshold for archiving")

    # server
    subparsers.add_parser("server", help="Run MCP stdio server")

    # embed-service
    p_embed_srv = subparsers.add_parser("embed-service", help="Run standalone embedding microservice")
    p_embed_srv.add_argument("--host", default="0.0.0.0", help="Bind host")
    p_embed_srv.add_argument("--port", type=int, default=8000, help="Bind port")
    p_embed_srv.add_argument("--model", default="all-MiniLM-L6-v2", help="Model name")

    # init
    p_init = subparsers.add_parser("init", help="Initialize local vault and generate agent MCP configuration")
    p_init.add_argument("--path", default="~/.mnemosyne/vault", help="Target Obsidian vault directory")

    # assemble-context
    p_ctx = subparsers.add_parser("assemble-context", help="Retrieve and pack memory into a token-budgeted prompt block")
    p_ctx.add_argument("query", help="Search query")
    p_ctx.add_argument("--max-tokens", type=int, default=2000, help="Maximum token budget")
    p_ctx.add_argument("--wing", default=None, help="Filter by wing")
    p_ctx.add_argument("--room", default=None, help="Filter by room")

    args = parser.parse_args()

    if not args.command or args.command == "server":
        server = MCPServer()
        server.run()
        return

    if args.command == "init":
        v_path = os.path.expanduser(args.path)
        os.makedirs(v_path, exist_ok=True)
        for w in ["general", "projects", "concepts", "archive", "sessions"]:
            os.makedirs(os.path.join(v_path, w), exist_ok=True)

        mem = UnifiedMemorySystem(vault_path=v_path)
        mem.remember(
            title="Welcome to Mnemosyne",
            content="# Welcome to Mnemosyne\n\nYour local-first hierarchical knowledge graph memory engine is ready.",
            tags=["welcome", "system"],
            salience=1.0,
            pinned=True,
        )

        mcp_config = {
            "mcpServers": {
                "mnemosyne": {
                    "command": "mnemosyne",
                    "args": ["server"],
                    "env": {
                        "MEMORY_VAULT_PATH": v_path,
                    },
                }
            }
        }

        print("=" * 60)
        print("🧠 Mnemosyne Initialized Successfully!")
        print("=" * 60)
        print(f"📁 Vault Path: {v_path}")
        print(f"💾 Storage Mode: Light Mode (SQLite WAL)")
        print("\n📋 Ready-to-copy MCP Configuration (Claude / Cursor / Hermes):")
        print(json.dumps(mcp_config, indent=2))
        print("=" * 60)
        return

    if args.command == "sync-gdrive":
        from mnemosyne.sync.gdrive import GoogleDriveSyncManager
        manager = GoogleDriveSyncManager(
            vault_path=args.vault_path,
            folder_name=args.folder,
            credentials_path=args.credentials,
        )
        if not manager.is_available():
            print(json.dumps({"error": "Google Drive client libraries missing. Install via: pip install 'mnemosyne[gdrive]'"}))
            sys.exit(1)
        if args.daemon:
            manager.run_daemon(interval_seconds=args.interval)
        else:
            res = manager.sync()
            print(json.dumps(res, indent=2))
        return

    if args.command == "embed-service":
        from mnemosyne.embed_service import run_service
        run_service(host=args.host, port=args.port, model_name=args.model)
        return

    mem = UnifiedMemorySystem(vault_path=args.vault_path, dsn=args.dsn, shared_dsn=args.shared_dsn)

    if args.command == "remember":
        res = mem.remember(
            args.title,
            args.content,
            tags=args.tags,
            salience=args.salience,
            wing=args.wing,
            room=args.room,
            pinned=args.pinned,
        )
        print(json.dumps(res, indent=2))

    elif args.command == "publish-shared":
        res = mem.publish_shared(
            args.title,
            args.content,
            tags=args.tags,
            wing=args.wing,
            room=args.room,
        )
        print(json.dumps(res, indent=2))

    elif args.command == "recall":
        scope = {}
        if args.wing:
            scope["wing"] = args.wing
        if args.room:
            scope["room"] = args.room
        results = mem.recall(args.query, mode=args.mode, top_k=args.top_k, scope=scope or None)
        print(json.dumps(results, indent=2, default=str))

    elif args.command == "assemble-context":
        scope = {}
        if args.wing:
            scope["wing"] = args.wing
        if args.room:
            scope["room"] = args.room
        res = mem.assemble_context(args.query, max_tokens=args.max_tokens, scope=scope or None)
        print(res.get("context_text", ""))
        print(f"\n<!-- Estimated tokens: {res.get('estimated_tokens')} | Notes included: {res.get('notes_included')} -->", file=sys.stderr)

    elif args.command == "timeline":
        res = mem.timeline(limit=args.limit)
        print(json.dumps(res, indent=2, default=str))

    elif args.command == "stats":
        res = mem.stats()
        print(json.dumps(res, indent=2))

    elif args.command == "consolidate":
        res = mem.consolidate(decay_rate=args.decay_rate, archive_threshold=args.archive_threshold)
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
