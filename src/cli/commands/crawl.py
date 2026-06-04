from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from cli.commands.base import add_project_dir_arg
from cli.crawler import ForgeCrawlError, crawl_project, dump_crawl_error, dump_crawl_result


def register_crawl(subparsers) -> None:
    parser = subparsers.add_parser("crawl", help="Crawl a Forge V4 project and embedded code annotations")
    add_project_dir_arg(parser)
    parser.add_argument("--format", choices=["json", "yaml", "md"], default="json")
    parser.set_defaults(func=run)


def run(args: Namespace) -> int:
    root = Path(args.project_dir).resolve() if args.project_dir else Path.cwd()
    try:
        result = crawl_project(root)
    except ForgeCrawlError as exc:
        print(dump_crawl_error(exc, args.format, root))
        return 1
    if args.format == "json":
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(dump_crawl_result(result, args.format))
    return 0
