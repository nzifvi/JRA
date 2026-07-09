import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import glob
import os
import sys
import re

def frame_sort_key(filepath):
    # Sort by the timestamp embedded in the filename (distance_<ts>.npz) so
    # frames play in capture order, not lexical order.
    m = re.search(r"distance_([\d.]+)\.npz", os.path.basename(filepath))
    return float(m.group(1)) if m else 0.0

def play_depth(folder, delay=1.0):
    pattern = os.path.join(folder, "distance_*.npz")
    files = sorted(glob.glob(pattern), key=frame_sort_key)

    if not files:
        print(f"No distance_*.npz files found in {folder}")
        return

    print(f"Found {len(files)} frames — playing with {delay}s delay. "
          f"Close the window to stop.")

    # Set up the figure ONCE and reuse it, updating the image data each frame.
    # Recreating the figure per frame would be slow and flicker.
    plt.ion()                              # interactive mode: draw without blocking
    fig, ax = plt.subplots(figsize=(10, 6))

    # Prime the display with the first frame to establish the image + colourbar.
    first = np.load(files[0])["distance"]
    masked0 = np.ma.masked_equal(first, 0)
    im = ax.imshow(masked0, cmap="turbo")
    cbar = fig.colorbar(im)
    cbar.set_label("Distance (m)")
    ax.set_xlabel("x (px)")
    ax.set_ylabel("y (px)")

    for i, fp in enumerate(files):
        if not plt.fignum_exists(fig.number):
            print("Window closed — stopping.")
            break

        data = np.load(fp)
        depth = data["distance"]
        timestamp = float(data["timestamp"])

        masked = np.ma.masked_equal(depth, 0)
        valid = depth[depth > 0]

        im.set_data(masked)
        if valid.size:
            im.set_clim(valid.min(), np.percentile(valid, 99))

        ax.set_title(f"Frame {i+1}/{len(files)}  "
                     f"t={timestamp:.2f}  "
                     f"{os.path.basename(fp)}")

        fig.canvas.draw_idle()
        plt.pause(delay)

    plt.ioff()
    print("Playback finished.")
    plt.show()

if __name__ == "__main__":
    play_depth(
        folder = r"C:\Users\benja\Desktop\D445Data",
        delay = 0.25
    )