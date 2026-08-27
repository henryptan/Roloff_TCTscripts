#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Reads multiple TCT CSV waveform files, sums their voltages point-by-point,
plots the resulting summed waveform with time in nanoseconds (ns), and optionally
exports the summed trace as a CSV file.

Usage:
  python sumWaveforms.py -f J2-99V.csv J3-99V.csv J14-99V.csv J15-99V.csv -o summed_plot.png
  python sumWaveforms.py -f *.csv -o summed_plot.png --csv_out summed_data.csv
"""

import argparse
import csv
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def sum_and_plot(csv_files, output_png, output_csv=None, hide_individual=False):
    datasets = []

    # Load all input CSV files
    for filepath in csv_files:
        times = []
        voltages = []
        with open(filepath, "r") as fd:
            reader = csv.reader(fd)
            next(reader, None)  # Skip header
            for row in reader:
                if row and len(row) >= 2:
                    times.append(float(row[0]))
                    voltages.append(float(row[1]))

        label = os.path.splitext(os.path.basename(filepath))[0]
        datasets.append({
            "name": label,
            "time_s": np.array(times),
            "voltage_v": np.array(voltages)
        })

    if not datasets:
        print("Error: No CSV data found.")
        return

    # Establish common time base from the first dataset
    ref_time_s = datasets[0]["time_s"]
    ref_time_ns = ref_time_s * 1e9
    total_voltage = np.zeros_like(ref_time_s)

    plt.figure(figsize=(9, 5.5))

    # Add individual traces as subtle dashed lines for comparison
    for ds in datasets:
        # Interpolate voltage values onto reference time grid in case of micro-sampling differences
        interp_voltage = np.interp(ref_time_s, ds["time_s"], ds["voltage_v"])
        total_voltage += interp_voltage

        if not hide_individual:
            plt.plot(ds["time_s"] * 1e9, ds["voltage_v"], linestyle="--", alpha=0.45, label=ds["name"])

    # Plot total summed trace
    plt.plot(ref_time_ns, total_voltage, color="crimson", linewidth=2.0, label="Summed Waveform")

    plt.xlabel("Time (ns)", fontsize=12)
    plt.ylabel("Voltage (V)", fontsize=12)
    plt.title("Summed TCT Waveforms", fontsize=14)
    plt.grid(True, linestyle="--", alpha=0.7)
    plt.legend(loc="best", frameon=True)
    plt.tight_layout()
    plt.savefig(output_png, dpi=300)
    plt.close()

    # Optional export of summed waveform to CSV
    if output_csv:
        with open(output_csv, "w") as fd:
            writer = csv.writer(fd)
            writer.writerow(["Time(s)", "Voltage(V)"])
            for t, v in zip(ref_time_s, total_voltage):
                writer.writerow([t, v])
        print("Exported summed CSV: %s" % output_csv)

    print("Saved summed plot: %s" % output_png)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sum voltage values from multiple TCT CSV files and plot the total in nanoseconds."
    )
    parser.add_argument(
        "-f", "--files", nargs="+", required=True, help="List of input CSV files", metavar=""
    )
    parser.add_argument(
        "-o", "--output", type=str, default="summed_plot.png", help="Output PNG file path (default: summed_plot.png)", metavar=""
    )
    parser.add_argument(
        "--csv_out", type=str, default=None, help="Optional output path to export summed CSV file", metavar=""
    )
    parser.add_argument(
        "--hide_individual", action="store_true", help="Hide individual sample traces and plot only the summed curve"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    sum_and_plot(args.files, args.output, args.csv_out, args.hide_individual)


if __name__ == "__main__":
    main()