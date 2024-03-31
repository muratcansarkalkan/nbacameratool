# NBA Live 2005-06 Camera Tool

NBA Live 2005-06 Camera Tool is a Python-based GUI tool for modifying values of the nbacam.mgd file, which is responsible for cameras used throughout the game.

As of now, you can edit position, rotation and zoom values for free throw cameras and most of the values in Press Box camera.

This tool only works with NBA Live 2005's nbacam.mgd, but the file can also be used for NBA Live 06 without any crashes. For now, I don't plan to create a tool for NBA Live 06's nbacam.mgd or 07 and 08.

## Prerequisites

- Python 3.10

## How to Use

1. **Download the Project:**
   - Click on the "Code" button and select "Download ZIP".
   - Extract the contents to your desired location.

2. **Run the Script:**
   - Open a command prompt.
   - Navigate to the project directory.
   - Type the following command:
     ```bash
     python main.py
     ```

## Basic rules of usage

- Edit the values to your wish. You can use either integers or floats to do so. The tool will convert the value you placed to a float.
- Make sure you enter your floats with ".", example, 4.38 instead of 4,38 or another sign.
- Before saving, click on another input before your last saved input. Example, if your last edit was on Position X at User Angle of Free Throw, click on another input before saving. Otherwise, the last value you placed, will not be saved. This will be addressed in upcoming versions.
- Positions have X, Y, Z values. These values can be directly compared with the dimensions of arenas.
- Rotations are evaluated as radians. For example, 1.5708 represent 90° degrees.
- Zoom values can be regarded as inverse of focal length. For instance, if the zoom value is decreased, the focal length increases. A smaller "zoom" value resembles real-life cameras.

## Hints

- For free throw cameras; 
   - Sometimes after editing camera, it might capture crowd instead of the court. Orientation of every camera can chnage. Feel free to change the rotation of Z by 90 degrees or -90 degrees for correct values.
- For press box cameras;
   - If you want same zoom for all zoom levels, make all the zoom values equal.
   - Some of the press box camera values are not tested. They are at Advanced Settings tab. You can test them to your wish, make sure to have a backup of your files in any event.
- The best way to prepare cameras for the game is to export models of a stadium and test them in Blender. For now, it is not possible to export entire stadium model from NBA Live 2005 files but this can be done for NBA Live 2004 by [OTools](https://bitbucket.org/fifam/otools/src/master/). The dimensions for stadiums and courts are equal.
   - Extract xxstd.o, xxstd.fsh, xxcrt.o and xxcrt.fsh from .viv files.
   - Export .o file and .fsh file contents using OTools to .gltf and .png files respectively.
   - Import .gltf file content in Blender and rotate the models by -90 degrees in X.
   - Rest is creating a camera in Blender and copying the values from Blender, to NBA Live Camera tool.

## Credits:

- Every modder who modified nbacam.mgd