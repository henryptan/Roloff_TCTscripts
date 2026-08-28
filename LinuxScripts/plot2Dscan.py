import os
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("scan2D.txt", sep=r"\s+", engine="python")

# Fallback for single-channel datasets missing Channel column
if "Channel" not in df.columns:
    df["Channel"] = 1

# Optional channel -> sensor name labels, written by runScan2D_R.sh when
# multiple sensors are scanned at the same time (one per channel)
channel_map = {}
if os.path.exists("channel_map.txt"):
    with open("channel_map.txt") as f:
        for line in f:
            line = line.strip()
            if not line or ":" not in line:
                continue
            ch_str, sensor_name = line.split(":", 1)
            try:
                channel_map[int(ch_str)] = sensor_name.strip()
            except ValueError:
                continue

unique_channels = df["Channel"].unique()

#finding the min/max for the color axis
vmin = df["Pairs"].min()
vmax = df["Pairs"].max()

fig, axes = plt.subplots(
    1, len(unique_channels), 
    figsize=(5.5 * len(unique_channels), 5), 
    squeeze=False
)

for idx, ch in enumerate(unique_channels):
    ax = axes[0, idx]
    sub_df = df[df["Channel"] == ch]
    grid = sub_df.pivot(index="y(um)", columns="x(um)", values="Pairs")
    
    im = ax.imshow(
        grid,
        origin="lower",
        aspect="equal",
        extent=[
            grid.columns.min(), grid.columns.max(),
            grid.index.min(), grid.index.max()
        ],
        cmap="viridis",
        vmin = vmin,
        vmax = vmax
    )
    
    ax.set_xlabel("x (um)")
    ax.set_ylabel("y (um)")
    sensor_label = channel_map.get(ch)
    title = f"Channel {ch} ({sensor_label}) - Pairs" if sensor_label else f"Channel {ch} - Pairs"
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label="Pairs")

plt.tight_layout()
plt.show()
