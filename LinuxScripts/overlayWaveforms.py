#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reads multiple TCT waveform CSV files and overlays them on a single plot.
Converts the time axis from seconds to nanoseconds (ns).

Usage:
  python overlayWaveforms.py -f J2-99V.csv J3-99V.csv J14-99V.csv J15-99V.csv -o overlay.png
  python overlayWaveforms.py -f *.csv -o overlay.png
"""

import argparse
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_overlay(csv_files, output_png, title):
    plt.figure(figsize=(9, 5.5))

    for filepath in csv_files:
        times_ns = []
        voltages_v = []

        with open(filepath, "r") as fd:
            reader = csv.reader(fd)
            next(reader, None)  # Skip CSV header
            for row in reader:
                if row and len(row) >= 2:
                    # Convert Time(s) to nanoseconds (ns)
                    times_ns.append(float(row[0]) * 1e9)
                    voltages_v.append(float(row[1]))

        # Extract filename without extension for legend label
        label = os.path.splitext(os.path.basename(filepath))[0]
        plt.plot(times_ns, voltages_v, label=label, linewidth=1.5)

    plt.xlabel("Time (ns)", fontsize=12)
    plt.ylabel("Voltage (V)", fontsize=12)
    plt.title(title, fontsize=14)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(title="Trace Name", loc="best", frameon=True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    plt.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Overlay multiple TCT CSV waveform traces on one plot with time in nanoseconds."
    )
    parser.add_argument(
        "-f", "--files", nargs="+", required=True, help="List of CSV files to overlay", metavar=""
    )
    parser.add_argument(
        "-o", "--output", type=str, default="overlay_waveforms.png", help="Output PNG path (default: overlay_waveforms.png)", metavar=""
    )
    parser.add_argument(
        "-t", "--title", type=str, default="Overlay of TCT Waveforms", help="Plot title", metavar=""
    )
    return parser.parse_args()


def main():
    args = parse_args()
    plot_overlay(args.files, args.output, args.title)
    print("Successfully generated overlay plot: %s" % args.output)


if __name__ == "__main__":
    main()