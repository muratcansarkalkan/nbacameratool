# NBA Live MGD Camera Editor v0.3.5-alpha

Experimental editor and Blender-preview tool for NBA Live camera MGD files.

## v0.3.5 changes

- Added **Help → Camera Parameter Guide** inside the application.
- Added **Confirmed / Likely / Experimental** research labels to recognized camera values.
- Added descriptions directly beside values in the main MGD editor and Press Box Designer.
- Updated **Live Broadcast** with the tested `Vertical target following = 45%` adjustment.
- Added `PressBoxCamera.md` with the current parameter map, tuning workflow, Memphis example, and symptom-to-control reference.

## Live Broadcast

The current preset uses:

- Dynamic zoom / push-in: 12%
- Aim freedom: 25%
- Vertical target following: 45%
- Horizontal rotation range: 50%
- Target-height influence: 30%
- Base framing range: 25%
- Distance compensation: 100% inverse
- Pan damping / viscosity: 130%
- Target-follow coupling: 85%
- Maximum pan speed: 55%
- Pan correction tolerance: 80%

Arena positions remain user-defined. A tested Memphis example is `(-3, -125, 45)`.

See `PressBoxCamera.md` for details.
