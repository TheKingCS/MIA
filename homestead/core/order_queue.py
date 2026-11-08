"""
MIA Homestead — To-Order Queue Review
v0.1

Lightweight terminal review for the auto-proposed reorder queue —
doesn't need the AI assistant or an API key running, just the database.
Nothing here ever places a real order; approving just confirms "yes,
go buy this" and clears it from the queue.

Usage:
    python3 core/order_queue.py --db mia_homestead.db
    python3 core/order_queue.py --db mia_homestead.db --list-only
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.inventory import InventoryManager


def format_item(item: dict) -> str:
    cost_str = f"~${item['cost']:.2f}" if item["cost"] else "cost unknown"
    supplier = item["supplier"] or "no supplier set"
    lines = [
        f"#{item['order_id']}  {item['name']}  ({item['category']})",
        f"    qty: {item['quantity']}{item['unit'] or ''}   {cost_str}   {supplier}",
    ]
    # supplier_url is real sourcing info a human can act on directly (not
    # just a name) -- was fetched by get_to_order_list() but silently
    # dropped here, found 2026-08-31 while working the "enrich order
    # proposals with real sourcing info" punch-list item.
    if item.get("supplier_url"):
        lines.append(f"    source: {item['supplier_url']}")
    lines.append(f"    reason: {item['notes'] or '—'}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--list-only", action="store_true", help="Just print the queue, don't prompt")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    inv = InventoryManager(conn)

    queue = inv.get_to_order_list()
    if not queue:
        print("To-order queue is empty. Nothing pending approval.")
        return

    print(f"\n{len(queue)} item(s) awaiting approval:\n")

    if args.list_only:
        for item in queue:
            print(format_item(item))
            print()
        return

    for item in queue:
        print("\n" + "-" * 50)
        print(format_item(item))
        while True:
            choice = input("  Approve / Deny / Skip? [a/d/s]: ").strip().lower()
            if choice in ("a", "approve"):
                inv.approve_order(item["order_id"])
                print("  -> approved. Go place the order when ready.")
                break
            elif choice in ("d", "deny"):
                reason = input("  Reason (optional): ").strip() or None
                inv.deny_order(item["order_id"], reason=reason)
                print("  -> denied, removed from queue.")
                break
            elif choice in ("s", "skip"):
                print("  -> skipped, still pending.")
                break
            else:
                print("  Please enter a, d, or s.")

    print("\nDone reviewing.")


if __name__ == "__main__":
    main()
