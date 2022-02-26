# VideoReference
Python module for importing video references in Autodesk Maya.

![videoReference loaded in Maya](/images/videoReferenceStill1.png)

# Video Tutorial:
[![Watch the video](/images/introSlate.png)](https://vimeo.com/667222084)

# How to install:

### Automated installation: (Requires internet connection to install opencv-python)
1. Unzip the archive.
2. Drag and drop the "dragDropInstaller.py" into the Maya 3d viewport.
3. Follow the steps on screen.

### Manual installation:
1. Close all running instances of Maya.
2. Make sure https://pypi.org/project/opencv-python/ is installed and that it is accessible by Maya. Please refer to https://knowledge.autodesk.com/support/maya/learn-explore/caas/CloudHelp/cloudhelp/2022/ENU/Maya-Scripting/files/GUID-72A245EC-CDB4-46AB-BEE0-4BBBF9791627-htm.html
3. Go to your Maya modules directory (create the "modules" folder if it does not exist):
```
(Windows) /Users/<username>/Documents/maya/modules/
(MacOS) $HOME/Library/Preferences/Autodesk/maya/modules/
(Linux)	$HOME/maya/modules/
```
4. Copy the "videoReference" folder and "videoReference.mod" file in the modules folder.
5. Start Maya, the module will be loaded and the console should print out:
```
// Successfully imported python module 'videoReference' v.X.X.X //
```

# How to use:
After loading the module in Maya, go to Create / Video Reference and choose a/some video file/s.

![videoReference loaded in Maya](/images/videoReferenceStill2.png)

# Supported Maya versions and platforms:
```
Maya 2022 - Python 3.7 (Windows, Linux, MacOS not yet tested but should work)
```

# Release Notes:
```
Version 1.0.0

Initial release
```