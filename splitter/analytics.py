"""
analytics.py - Expense summaries and charts for Previous Rooms.

UNIT III (NumPy + Pandas):
  * pd.DataFrame built from a list of dicts.
  * Filtering with boolean masks (df[df["role"] == "owner"]).
  * groupby() + agg() for spending per activity and per month.
  * NumPy: np.sum, np.mean, np.median, np.max, np.std on the share column.

UNIT V (Data Visualisation):
  * Matplotlib draws a two-panel chart (by activity, by month) into an
    in-memory PNG that Flask serves at /api/users/<username>/chart.png.
"""
import io

import matplotlib
matplotlib.use("Agg")                # no window needed: render straight to PNG
import matplotlib.pyplot as plt      # noqa: E402
import numpy as np                   # noqa: E402
import pandas as pd                  # noqa: E402

COLUMNS = ["code", "name", "activity", "date", "role", "my_share", "total_amount", "total_people"]
ACCENT = "#4F46E5"
MUTED = "#9CA3AF"


def build_expense_frame(previous_rooms):
    df = pd.DataFrame(previous_rooms, columns=COLUMNS)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%b %Y")
    df["month_sort"] = df["date"].dt.to_period("M")
    df["my_share"] = df["my_share"].astype(float)
    return df


def _records(frame):
    """DataFrame -> list of plain-Python dicts (NumPy types are not JSON serialisable)."""
    return [
        {key: (round(float(value), 2) if isinstance(value, (float, np.floating)) else
               int(value) if isinstance(value, np.integer) else value)
         for key, value in row.items()}
        for row in frame.to_dict("records")
    ]


def summarize(active_rooms, previous_rooms):
    df = build_expense_frame(previous_rooms)

    # Money still in motion across active rooms (NumPy arrays)
    to_collect = np.array([r.get("outstanding", 0) for r in active_rooms if r["role"] == "owner"], dtype=float)
    to_pay = np.array([r["my_share"] or 0 for r in active_rooms if r["role"] == "participant"], dtype=float)

    summary = {
        "rooms_count": 0,
        "total_spent": 0.0,
        "average_share": 0.0,
        "median_share": 0.0,
        "max_share": 0.0,
        "std_share": 0.0,
        "fronted_as_owner": 0.0,
        "rooms_owned": 0,
        "rooms_joined": 0,
        "top_activity": None,
        "by_activity": [],
        "by_month": [],
        "pending_to_collect": round(float(np.sum(to_collect)), 2),
        "pending_to_pay": round(float(np.sum(to_pay)), 2),
    }
    if df.empty:
        return summary

    shares = df["my_share"].to_numpy()
    owned = df[df["role"] == "owner"]                 # boolean-mask filtering

    by_activity = (
        df.groupby("activity")["my_share"]
        .agg(total="sum", rooms="count", average="mean")
        .reset_index()
        .sort_values("total", ascending=False)
    )
    by_month = (
        df.groupby(["month_sort", "month"])["my_share"]
        .sum()
        .reset_index()
        .sort_values("month_sort")
        .drop(columns="month_sort")
        .rename(columns={"my_share": "total"})
    )

    summary.update({
        "rooms_count": int(len(df)),
        "total_spent": round(float(np.sum(shares)), 2),
        "average_share": round(float(np.mean(shares)), 2),
        "median_share": round(float(np.median(shares)), 2),
        "max_share": round(float(np.max(shares)), 2),
        "std_share": round(float(np.std(shares)), 2),
        "fronted_as_owner": round(float(owned["total_amount"].sum()), 2),
        "rooms_owned": int(len(owned)),
        "rooms_joined": int(len(df) - len(owned)),
        "top_activity": str(by_activity.iloc[0]["activity"]),
        "by_activity": _records(by_activity),
        "by_month": _records(by_month),
    })
    return summary


def spending_chart_png(previous_rooms, username=""):
    df = build_expense_frame(previous_rooms)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=110)
    fig.patch.set_facecolor("white")

    if df.empty:
        for ax in axes:
            ax.axis("off")
        axes[0].text(1.0, 0.5, "No past expenses yet.\nSettle a room to see your chart.",
                     ha="center", va="center", fontsize=12, color=MUTED, transform=axes[0].transAxes)
    else:
        by_activity = df.groupby("activity")["my_share"].sum().sort_values()
        axes[0].barh(by_activity.index, by_activity.values, color=ACCENT)
        axes[0].set_title("Spending by activity", loc="left", fontsize=11, fontweight="bold")
        for y, value in enumerate(by_activity.values):
            axes[0].text(value, y, f"  ₹{value:,.0f}", va="center", fontsize=9)
        axes[0].set_xlim(0, by_activity.max() * 1.3)

        by_month = df.groupby("month_sort")["my_share"].sum().sort_index()
        labels = [period.strftime("%b %y") for period in by_month.index]
        axes[1].bar(labels, by_month.values, color=ACCENT, width=0.6)
        axes[1].set_title("Spending by month", loc="left", fontsize=11, fontweight="bold")
        axes[1].set_ylabel("Amount (₹)")

        for ax in axes:
            ax.spines[["top", "right"]].set_visible(False)
            ax.tick_params(labelsize=9)
            ax.grid(axis="x" if ax is axes[0] else "y", color="#E5E7EB", linewidth=0.8)
            ax.set_axisbelow(True)

    if username:
        fig.suptitle(f"{username}'s past expenses", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png")
    plt.close(fig)                   # free memory on the server
    buffer.seek(0)
    return buffer
