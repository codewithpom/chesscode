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
    batch.add_argument("action", choices=["plan"])
    batch.add_argument("--tier", choices=["floor", "target"], required=True)

    upload = sub.add_parser("upload")
    upload.add_argument("--video", required=True)
    upload.add_argument("--repair", action="store_true")

    auth = sub.add_parser("auth")
    auth.add_argument("action", choices=["check", "login"])

    qa = sub.add_parser("qa")
    qa.add_argument("--video", required=True)

    ledger = sub.add_parser("ledger")
    ledger.add_argument("action", choices=["verify"])
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    module = importlib.import_module(COMMANDS[args.command])
    return module.main(args)


if __name__ == "__main__":
    sys.exit(main())
