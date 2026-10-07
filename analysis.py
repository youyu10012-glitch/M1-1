"""Collect and analyze Seoul daily mean temperature from Open-Meteo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "seoul_daily_temperature_2024_2025.csv"
IMAGE_DIR = ROOT / "images"
START_DATE = "2024-01-01"
END_DATE = "2025-12-31"
LATITUDE = 37.5665
LONGITUDE = 126.9780


def fetch_data() -> pd.DataFrame:
    params = urlencode(
        {
            "latitude": LATITUDE,
            "longitude": LONGITUDE,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "daily": "temperature_2m_mean",
            "timezone": "Asia/Seoul",
        }
    )
    url = f"https://archive-api.open-meteo.com/v1/archive?{params}"
    with urlopen(url, timeout=30) as response:
        payload = json.load(response)

    daily = payload["daily"]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temperature_mean_c": daily["temperature_2m_mean"],
        }
    )


def load_data(refresh: bool) -> tuple[pd.DataFrame, dict[str, int]]:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if refresh or not DATA_PATH.exists():
        raw = fetch_data()
        raw.to_csv(DATA_PATH, index=False, date_format="%Y-%m-%d")
    else:
        raw = pd.read_csv(DATA_PATH, parse_dates=["date"])

    original_rows = len(raw)
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["temperature_mean_c"] = pd.to_numeric(
        raw["temperature_mean_c"], errors="coerce"
    )
    raw = raw.dropna(subset=["date"]).sort_values("date")
    duplicate_count = int(raw["date"].duplicated().sum())
    raw = raw.drop_duplicates(subset=["date"], keep="last").set_index("date")

    expected_dates = pd.date_range(START_DATE, END_DATE, freq="D")
    raw = raw.reindex(expected_dates)
    raw.index.name = "date"
    missing_before = int(raw["temperature_mean_c"].isna().sum())
    if missing_before > 2:
        raise ValueError(
            f"Missing {missing_before} temperature values; inspect the source before analysis."
        )
    if missing_before:
        raw["temperature_mean_c"] = raw["temperature_mean_c"].interpolate(
            method="time", limit=2, limit_area="inside"
        )
    if raw["temperature_mean_c"].isna().any():
        raise ValueError("Temperature values remain missing after limited interpolation.")

    temperatures = raw["temperature_mean_c"]
    implausible_count = int(((temperatures < -35) | (temperatures > 45)).sum())
    if implausible_count:
        raise ValueError(
            f"Found {implausible_count} values outside the broad Seoul plausibility range [-35, 45] C."
        )

    audit = {
        "source_rows": original_rows,
        "duplicate_dates_removed": duplicate_count,
        "missing_values_before_interpolation": missing_before,
        "implausible_values_outside_-35_to_45_c": implausible_count,
    }
    return raw, audit


def make_plots(data: pd.DataFrame) -> None:
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.plot(data.index, data["temperature_mean_c"], color="#91a6b2", linewidth=0.8,
            alpha=0.75, label="Daily mean")
    ax.plot(data.index, data["rolling_30d"], color="#c34f36", linewidth=2.2,
            label="30-day moving average")
    ax.set(title="Seoul daily mean temperature, 2024-2025",
           xlabel="Date", ylabel="Temperature (C)")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    fig.savefig(IMAGE_DIR / "01_daily_and_rolling_mean.png", dpi=160)
    plt.close(fig)

    monthly = data.groupby(data.index.month)["temperature_mean_c"]
    means = monthly.mean()
    stds = monthly.std()
    fig, ax = plt.subplots(figsize=(10, 5.5))
    months = np.arange(1, 13)
    ax.bar(months, means, yerr=stds, color="#287d78", alpha=0.88,
           capsize=4, error_kw={"elinewidth": 1})
    ax.set_xticks(months, [f"{month:02d}" for month in months])
    ax.set(title="Monthly temperature pattern (mean +/- daily standard deviation)",
           xlabel="Month", ylabel="Temperature (C)")
    fig.tight_layout()
    fig.savefig(IMAGE_DIR / "02_monthly_pattern.png", dpi=160)
    plt.close(fig)

    monthly_by_year = data.groupby([data.index.year, data.index.month])["temperature_mean_c"].mean()
    heatmap = monthly_by_year.unstack(level=0)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    image = ax.imshow(heatmap.to_numpy(), aspect="auto", cmap="RdYlBu_r")
    ax.set_xticks(np.arange(len(heatmap.columns)), heatmap.columns.astype(str))
    ax.set_yticks(np.arange(12), [f"{month:02d}" for month in heatmap.index])
    ax.set(title="Monthly mean temperature by year", xlabel="Year", ylabel="Month")
    for row in range(heatmap.shape[0]):
        for column in range(heatmap.shape[1]):
            ax.text(column, row, f"{heatmap.iloc[row, column]:.1f}",
                    ha="center", va="center", fontsize=9)
    fig.colorbar(image, ax=ax, label="Temperature (C)")
    fig.tight_layout()
    fig.savefig(IMAGE_DIR / "03_monthly_year_comparison.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    changes = data["daily_change_c"].dropna()
    ax.plot(changes.index, changes, color="#536e9b", linewidth=0.8)
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.axhline(3, color="#c34f36", linestyle="--", linewidth=1, label="+/- 3 C guide")
    ax.axhline(-3, color="#c34f36", linestyle="--", linewidth=1)
    ax.set(title="Day-to-day temperature change", xlabel="Date", ylabel="Change (C)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(IMAGE_DIR / "04_daily_change.png", dpi=160)
    plt.close(fig)


def print_summary(data: pd.DataFrame, audit: dict[str, int]) -> None:
    monthly = data.groupby(data.index.month)["temperature_mean_c"].mean()
    daily_change = data["daily_change_c"].dropna()
    largest_change_date = daily_change.abs().idxmax()
    seasonal_means = data.groupby("season")["temperature_mean_c"].mean()
    summary = {
        "period": [str(data.index.min().date()), str(data.index.max().date())],
        "data_points": len(data),
        "annual_mean_c": data.groupby(data.index.year)["temperature_mean_c"].mean().round(2).to_dict(),
        "monthly_mean_c": monthly.round(2).to_dict(),
        "warmest_month": int(monthly.idxmax()),
        "coldest_month": int(monthly.idxmin()),
        "monthly_mean_amplitude_c": round(float(monthly.max() - monthly.min()), 2),
        "hottest_day": str(data["temperature_mean_c"].idxmax().date()),
        "hottest_day_mean_c": round(float(data["temperature_mean_c"].max()), 2),
        "coldest_day": str(data["temperature_mean_c"].idxmin().date()),
        "coldest_day_mean_c": round(float(data["temperature_mean_c"].min()), 2),
        "largest_absolute_daily_change_date": str(largest_change_date.date()),
        "largest_absolute_daily_change_c": round(float(daily_change.loc[largest_change_date]), 2),
        "seasonal_mean_c": seasonal_means.round(2).to_dict(),
        "audit": audit,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Download data again from Open-Meteo.")
    args = parser.parse_args()

    data, audit = load_data(args.refresh)
    data["rolling_30d"] = data["temperature_mean_c"].rolling(30, min_periods=15).mean()
    data["daily_change_c"] = data["temperature_mean_c"].diff()
    data["rolling_30d_std"] = data["temperature_mean_c"].rolling(30, min_periods=15).std()
    data["season"] = ((data.index.month % 12) // 3).map(
        {0: "winter", 1: "spring", 2: "summer", 3: "autumn"}
    )

    make_plots(data)
    print_summary(data, audit)
    print(f"\nData: {DATA_PATH.relative_to(ROOT)}")
    print(f"Charts: {IMAGE_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()