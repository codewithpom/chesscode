"""dashboard.py — CLI dashboard showing content queue and schedule status."""

from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from config import cfg
from content_calendar import ContentCalendar


def show() -> None:
    """Print the full dashboard to stdout using rich."""
    console = Console()
    cal = ContentCalendar(cfg.db_path)
    status = cal.get_status()

    console.print(Panel("[bold cyan]ChessCode Content Dashboard[/bold cyan]", expand=False))

    # ── Content Queue ──────────────────────────────────────────────────────────
    queue = status["queue"]
    q_table = Table(title="Content Queue", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    q_table.add_column("ID", justify="right", width=4)
    q_table.add_column("Type", width=8)
    q_table.add_column("Title", min_width=30)
    q_table.add_column("Priority", justify="center", width=8)
    q_table.add_column("Status", width=12)
    q_table.add_column("Added", width=20)

    status_colors = {
        "pending": "yellow",
        "processing": "cyan",
        "done": "green",
        "failed": "red",
    }

    for row in queue:
        color = status_colors.get(row["status"], "white")
        q_table.add_row(
            str(row["id"]),
            row["content_type"],
            row["title"],
            str(row["priority"]),
            f"[{color}]{row['status']}[/{color}]",
            str(row["created_at"])[:19],
        )

    if not queue:
        q_table.add_row("—", "—", "[dim]Queue is empty[/dim]", "—", "—", "—")

    console.print(q_table)

    # ── Scheduled Uploads ──────────────────────────────────────────────────────
    scheduled = status["scheduled"]
    s_table = Table(title="Scheduled Uploads", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    s_table.add_column("ID", justify="right", width=4)
    s_table.add_column("Title", min_width=25)
    s_table.add_column("Lang", width=5)
    s_table.add_column("Scheduled At (UTC)", width=20)
    s_table.add_column("YouTube ID", width=14)
    s_table.add_column("Status", width=10)

    for row in scheduled:
        color = status_colors.get(row["status"], "white")
        yt_id = row.get("youtube_id") or "—"
        title = row.get("title") or "—"
        s_table.add_row(
            str(row["id"]),
            title,
            row["language"],
            str(row["scheduled_at"])[:19],
            yt_id,
            f"[{color}]{row['status']}[/{color}]",
        )

    if not scheduled:
        s_table.add_row("—", "[dim]No uploads scheduled[/dim]", "—", "—", "—", "—")

    console.print(s_table)

    # ── Next Upload Slots ──────────────────────────────────────────────────────
    slots = cal.next_upload_slots(count=4)
    console.print(
        Panel(
            "\n".join(f"  {s.strftime('%A %Y-%m-%d %H:%M UTC')}" for s in slots),
            title="Next 4 Upload Slots (Mon+Thu 09:00 IST)",
            expand=False,
        )
    )


if __name__ == "__main__":
    show()
