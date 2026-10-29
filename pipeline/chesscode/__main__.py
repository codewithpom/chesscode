"""CLI entry point (spec section 2). Each subcommand lives in its own module,
imported lazily so workstreams can add modules without touching this file."""
import argparse
import importlib
import sys

# subcommand -> module exposing main(args: argparse.Namespace) -> int
COMMANDS = {
    "run": "chesscode.runner",
    "batch": "chesscode.batch",
    "upload": "chesscode.upload",
    "auth": "chesscode.auth",
    "qa": "chesscode.qa",
    "ledger": "chesscode.ledger",
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="chesscode")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("--video", required=True)
    run.add_argument("--stage")
    run.add_argument("--until")

    batch = sub.add_parser("batch")
    batch.add_argument("--video", required=True)
    batch.add_argument("--upload", action="store_true")
    batch.add_argument("--batch-id")

    upload = sub.add_parser("upload")
    upload.add_argument("--video")
    upload.add_argument("--repair", action="store_true")
    upload.add_argument("--create-playlists", action="store_true")

    auth = sub.add_parser("auth")
    auth.add_argument("action", choices=["check", "login"])

    qa = sub.add_parser("qa")
    qa.add_argument("--video", required=True)
    qa.add_argument("--mp4", required=True)
    qa.add_argument("--thumb", required=True)

    ledger = sub.add_parser("ledger")
    ledger.add_argument("action", choices=["check", "collect"])
    ledger.add_argument("--artifacts")
    ledger.add_argument("--run-url", default="")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "upload" and not (args.video or args.create_playlists):
        parser.error("upload needs --video or --create-playlists")
    module = importlib.import_module(COMMANDS[args.command])
    return module.main(args)


if __name__ == "__main__":
    sys.exit(main())
