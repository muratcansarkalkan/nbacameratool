# Press Box Camera Guide

This guide documents the current reverse-engineered Press Box camera controls in NBA Live camera MGD files. Labels are intentionally split into **Confirmed**, **Likely**, and **Experimental** so tested behavior is not mixed with hypotheses.

## Recommended workflow

1. Open the original `nbacam.mgd`.
2. Open **Tools → Press Box Designer**.
3. Enter the arena-specific Press Box XYZ position.
4. Click **Live Broadcast**.
5. Click **Apply Broadcast Build**.
6. Save the MGD and test it in-game.
7. When fine-tuning, change one parameter family at a time.

## Live Broadcast baseline

| Control | Value |
|---|---:|
| Dynamic zoom / push-in | 12% |
| Aim freedom | 25% |
| Vertical target following | 45% |
| Horizontal rotation range | 50% |
| Target-height influence | 30% |
| Base framing range | 25% |
| Distance compensation | 100%, Inverse |
| Pan damping / viscosity | 130% |
| Target-follow coupling | 85% |
| Maximum pan speed | 55% |
| Pan correction tolerance | 80% |

The preset changes camera/controller behavior but does not force an arena position.

### Memphis example

A tested Memphis Press Box position is:

```text
X = -3
Y = -125
Z = 45
```

This is an arena-specific mount position, not a universal NBA Live 2005 value.

## Confirmed / strongly tested

### `position`
Physical camera location in game coordinates: X, Y, Z.

### `zoom_min_*` / `zoom_max_*`
Base framing range. In long-distance Press Box tests, smaller values tightened the view. Inverse distance compensation has worked when the physical camera is moved farther from the court.

### `scaletargety_*`
Position-aware vertical pitch/following. Increasing this improved vertical composition when the action moved to a different depth/side of the court.

Practical use: if players become too high or too low in the frame as play moves around the court, adjust **Vertical target following**.

### `hmin_*` / `hmax_*`
Horizontal heading/swivel envelope. Narrower span means a more static camera; wider span allows more left/right rotation.

### `orientationmaxv*`
Maximum pan/angular speed. Lower values reduce whip-pans.

## Likely

### `maxaimoffset_*`
Aim freedom/clamp. Lower values keep the composition more anchored; higher values allow a larger aim deviation.

### `aimtargetzratio`
Target-height influence. This is the strongest current candidate for making the camera pitch upward more when a shot, lob, or tracked target rises vertically.

Practical use: if the camera follows court position correctly but does not look high enough on jump shots, test **Target-height influence** first. If it appears capped, test `maxaimoffset_*` next.

### `orientationvisc*`
Pan damping/resistance. Higher generally makes movement feel heavier and smoother.

### `orientationcoup*`
How strongly orientation follows the calculated target.

### `maxzoomdiff`, `zoomdiff_*`, `pitch_zoomdiff_*`
Dynamic/situational zoom family. These appear to govern gameplay-driven push-ins and zoom variation. Lower values reduce zoom pumping.

## Experimental

### `zoom_netdist_min/max`
Appears to define a gameplay-distance window relative to the basket/net. This is not treated as physical camera-to-court distance and remains separate from the Live Broadcast preset.

### `orientationtole*`
Likely orientation correction tolerance/dead-zone. Exact runtime behavior is not yet established.

### `dunkdelaytime_*`
Likely timing/delay for dunk-related camera behavior.

## Symptom-to-control reference

| Symptom | First control to try |
|---|---|
| Action too high/low depending on court position | Vertical target following / `scaletargety_*` |
| Camera does not pitch up enough on shots/lobs | Target-height influence / `aimtargetzratio` |
| Too much left/right rotation | Horizontal rotation range / `hmin_*`, `hmax_*` |
| Pan is too fast / whips | Maximum pan speed / `orientationmaxv*` |
| Pan feels twitchy | Increase Pan damping / `orientationvisc*` |
| Camera is too loosely centered | Reduce Aim freedom / `maxaimoffset_*` |
| Too much zoom pumping | Reduce Dynamic zoom / `zoomdiff_*` family |
| Farther camera becomes too wide | Use Inverse distance compensation |

These interpretations will be refined as more in-game tests establish the controller math.
