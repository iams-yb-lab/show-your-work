"""Report exposure statistics for a rendered PNG, so light levels get tuned to a number.

    blender --background --factory-startup --python tools/measure_exposure.py -- img.png

Uses Blender's own image loading (numpy is bundled, PIL is not guaranteed). Values are
display-referred, i.e. post-AgX, so 1.0 really is clipped white.
"""

import sys
from pathlib import Path

import bpy
import numpy as np

for path in [Path(p) for p in sys.argv[sys.argv.index("--") + 1:]]:
    img = bpy.data.images.load(str(path.resolve()))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(-1, img.channels)
    rgb, alpha = px[:, :3], (px[:, 3] if img.channels == 4 else None)

    # Ignore fully transparent pixels; they carry no exposure information.
    if alpha is not None and (alpha > 0.001).any():
        rgb = rgb[alpha > 0.001]

    luma = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    print(f"{path.name}  {img.size[0]}x{img.size[1]}")
    print(f"  mean luma      {luma.mean():.4f}   (aim 0.16 - 0.34)")
    print(f"  median luma    {np.median(luma):.4f}")
    print(f"  p99 luma       {np.percentile(luma, 99):.4f}")
    print(f"  clipped >0.995 {100 * (luma > 0.995).mean():.2f} %   (aim < 1 %)")
    print(f"  crushed <0.005 {100 * (luma < 0.005).mean():.2f} %")
    bpy.data.images.remove(img)
