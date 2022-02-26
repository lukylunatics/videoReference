# Built-in imports
import os
import sys
import subprocess as sp

# Third-Party imports
from PySide2 import QtCore
import maya.cmds as cmds
from maya.app.startup import basic



MODULENAME = "videoReference"
DRAGGEDFROMPATH = os.path.dirname(__file__)
MAYAPY = f"\"{os.environ['MAYA_LOCATION']}/bin/mayapy\""
DEFAULTMODULEPATH = f"{os.environ['MAYA_APP_DIR']}/modules"
DEFAULTSCRIPTSPATH = f"{os.environ['MAYA_APP_DIR']}/scripts"
# Custom module path definitions
MODULESCRIPTSPATH = f"{DEFAULTMODULEPATH}/{MODULENAME}/scripts"
# List of required files to install
INSTALLATIONPACKAGE = [
	f"{DRAGGEDFROMPATH}/{MODULENAME}/scripts/{MODULENAME}.py",
	f"{DRAGGEDFROMPATH}/{MODULENAME}/scripts/userSetup.py",
	f"{DRAGGEDFROMPATH}/{MODULENAME}/icons/{MODULENAME}.png",
	f"{DRAGGEDFROMPATH}/{MODULENAME}.mod"
]

def validatePythonVersion():
	"""Validates the required python version."""
	if os.environ['MAYA_PYTHON_VERSION'] == "2":
		raise RuntimeError("Module requires Python 3, aborting installation!")

def validateInstallationFiles():
	"""Checks if all required installation files exist in source."""
	missingFiles = []
	for pkg in INSTALLATIONPACKAGE:
		if not QtCore.QFileInfo(pkg).exists():
			missingFiles.append(pkg)
	
	if missingFiles:
		raise RuntimeError(
			f"Installation package reported missing files: {missingFiles}, aborting!"
		)

def installDependencies() -> bool:
	"""Install required dependecies.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

	"""
	command = f"{MAYAPY} -m pip install --user opencv-python"
	try:
		output = sp.check_output(command, shell=True, stderr=sp.STDOUT, universal_newlines=True)
		print(f"// Pip install output: //\n{output}\n// Successfully installed all dependencies. //")
	except sp.CalledProcessError:
		print("// Could not resolve all dependencies. Installation did not complete! //")
		return False
	
	return True

def _removePreviousModule():
	"""Removes previous installation of the given module."""
	installationDestination = QtCore.QDir(f"{DEFAULTMODULEPATH}/{MODULENAME}")
	if installationDestination.exists():
		installationDestination.removeRecursively()

	previousModFile = QtCore.QFile(f"{DEFAULTMODULEPATH}/{MODULENAME}.mod")
	if previousModFile.exists():
		previousModFile.remove()

def _createDirsForCopying():
	"""TODO: Create a proper recrusive functrion for copying files over - temp workaround
	but at least we don't have to deal with '\\' '/' slashes
	"""
	modulePath = QtCore.QDir(DEFAULTMODULEPATH)
	modulePath.mkpath(f"{MODULENAME}/scripts/")
	modulePath.mkpath(f"{MODULENAME}/icons/")

def clearMemory():
	"""Clean the current sys.path and sys.modules from anything to do with MODULENAME."""
	pathsList = sys.path[:]
	for index, path in enumerate(pathsList[::-1]):
		if MODULENAME in path.lower():
			sys.path.remove(path)

	for module in list(sys.modules):
		if MODULENAME in module:
			del sys.modules[module]

def createDialog(message="Default Message", title="Default Title",	icon="question",
		buttons=["Install", "Cancel"], cancelButton="Cancel"
	) -> str:
	"""Convinience wrapper method for creating confirmDialogs."""
	return cmds.confirmDialog(
		title=title,
		message=message,
		icon=icon,
		button=buttons,
		cancelButton=cancelButton,
		dismissString=cancelButton
	)

def _finalizeInstallation():
	"""Performs final installation procedures."""
	clearMemory()
	
	# Add path if its not already there
	if not MODULESCRIPTSPATH in sys.path:
		sys.path.append(MODULESCRIPTSPATH)

	# Reload all the modules
	cmds.loadModule(scan=True)
	cmds.loadModule(allModules=True)

	# Reload userSetup files
	basic.executeUserSetup()

def onMayaDroppedPythonFile(*args, **kwargs):
	"""Main function that runs when dragging the file into Maya.

	Installation is performed by copying the module to the user preferences and creating
	a module file.

	"""
	validatePythonVersion()

	validateInstallationFiles()

	input = createDialog(
		message=f"This will install {MODULENAME} in:\n{DEFAULTMODULEPATH}",
		title=f"{MODULENAME} Installer"
	)
	if input == "Cancel":
		raise RuntimeError(f"Installation of {MODULENAME} has been cancelled.")
	else:

		if not installDependencies():
			input = createDialog(
				message=f"Installing dependencies failed, do you wish to continue or cancel the installation?",
				title=f"{MODULENAME} Failed to install dependencies."
			)
			if input == "Cancel":
				raise RuntimeError(f"Installation of {MODULENAME} has been cancelled.")
		else:

			_removePreviousModule()

			_createDirsForCopying()

			finished = False
			for pkg in INSTALLATIONPACKAGE:
				pkgQt = QtCore.QFile(pkg)
				finished = pkgQt.copy(pkg.replace(DRAGGEDFROMPATH, DEFAULTMODULEPATH))

			if finished:
				_finalizeInstallation()
