from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


def main() -> None:
    output = Path("sample_data/EUR_USD_DEMO_H1.csv")
    output.parent.mkdir(exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    price = 1.1000
    changes = (
        [-0.00020] * 80
        + [0.00035] * 70
        + [-0.00035] * 70
        + [0.00030] * 70
        + [-0.00030] * 70
        + [0.00025] * 70
    )

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "open", "high", "low", "close", "volume"])
        for index, change in enumerate(changes):
            open_price = price
            price += change
            writer.writerow(
                [
                    (start + timedelta(hours=index)).isoformat(),
                    f"{open_price:.5f}",
                    f"{max(open_price, price) + 0.00060:.5f}",
                    f"{min(open_price, price) - 0.00060:.5f}",
                    f"{price:.5f}",
                    100,
                ]
            )


if __name__ == "__main__":
    main()
