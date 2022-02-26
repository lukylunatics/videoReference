# Third-Party imports
from maya import cmds
from maya import utils

# Custom Imports
from videoReference import VideoReference

moduleName = "videoReference"

def addMenuItem():
	if not cmds.about(batch=True):
		VideoReference.createMenuItems()

utils.executeDeferred(addMenuItem)

print(f"// Successfully imported python module '{moduleName}' v.1.0.0 //")
