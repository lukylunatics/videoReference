# Built-in imports
import os
import sys
import logging
import subprocess as sp
from typing import List

# Third-party imports
from PySide2 import QtCore as qtc

from maya import cmds
from maya.app.startup import basic



logger = logging.getLogger("DragDropInstall")
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)



class DragDropInstall():
	"""Base class for drag and drop install deployments of modules in Autodesk Maya."""

	moduleName = "videoReference"
	dependencies = "opencv-python"

	# Python
	mayaPy = f"\"{os.environ['MAYA_LOCATION']}/bin/mayapy\""
	mayaPythonVersion = int(os.environ['MAYA_PYTHON_VERSION'])

	# Paths
	draggedFromPath = os.path.dirname(__file__)
	defaultModulePath = f"{os.environ['MAYA_APP_DIR']}/modules"
	defaultScriptsPath = f"{os.environ['MAYA_APP_DIR']}/scripts"
	moduleScriptPath = f"{defaultModulePath}/{moduleName}/scripts"

	# Files
	installationFiles = [
		f"{draggedFromPath}/{moduleName}/scripts/{moduleName}.py",
		f"{draggedFromPath}/{moduleName}/scripts/userSetup.py",
		f"{draggedFromPath}/{moduleName}/icons/{moduleName}.png",
		f"{draggedFromPath}/{moduleName}.mod"
	]
	existingFiles = [
		f"{defaultModulePath}/{moduleName}",
		f"{defaultModulePath}/{moduleName}.mod"
	]

	def __str__(self) -> str:
		return f"Drag and drop installer for '{self.moduleName}' - Lukasstudio 2022."

	def validatePythonVersion(self, requiredVersion=3) -> bool:
		"""Validate the required python version.

		Args:
			requiredVersion (int): Required python version for the validation to be successfull.

		Returns:
			bool: If the python version is lower than the requiredVersion, it will return False,
				otherwise True

		"""
		logStr = f": Required python version is '{requiredVersion}' or higher, running '{self.mayaPythonVersion}'."

		if self.mayaPythonVersion >= requiredVersion:
			logger.info(f"PASSED {logStr}")
			return True

		logger.critical(f"FAILED {logStr}")
		return False

	def validateInstallationFiles(self) -> bool:
		"""Checks if all required installation files exist in source directory.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		missingFiles = []
		for file in self.installationFiles:
			if not qtc.QFileInfo(file).exists(): missingFiles.append(file)

		if len(missingFiles) == 0:
			logger.info("PASSED : Find all installation files.")
			return True

		logger.critical(f"FAILED : Found missing installation files {missingFiles}.")
		return False

	def checkPermissions(self) -> bool:
		"""Checks if you have read and write permissions in the destination directory.
		"""
		pass

	def unloadPlugin(self) -> bool:
		"""If the plugin is loaded unload it."""
		pass

	def removeExistingVersion(self) -> None:
		"""Removes all files from existing installation.

		If files from existing installation have been found, they will be removed.

		"""
		for path in self.existingFiles:
			fileInfo = qtc.QFileInfo(path)
			if fileInfo.exists():
				if fileInfo.isDir(): qtc.QDir(path).removeRecursively()
				if fileInfo.isFile(): qtc.QFile(path).remove()
	
		logger.info("PASSED : Remove existing installation files if they exist.")

	def installDependencies(self):
		"""Install required dependecies by calling the mayapy pip package manager.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		command = f"{self.mayaPy} -m pip install --user {self.dependencies}"
		try:
			output = sp.check_output(command, shell=True, stderr=sp.STDOUT, universal_newlines=True)
			logger.info(
				f"Pip install output:"
				f"\n{output}"
			)
			logger.info("PASSED : Install dependencies.")
		except sp.CalledProcessError:
			logger.critical("FAILED : Dependecies could not be installed")
			return False

		return True

	def validateFileInfo(self, path) -> qtc.QFileInfo or False:
		"""Validate the specified file.

		Args:
			path (str): Path to the object.

		Returns:
			fileInfo (QFileInfo): If the specified object exists it will be returned,
				if it does not exist False will be returned instead.

		"""
		fileInfo = qtc.QFileInfo(path)
		if fileInfo.exists():
			logger.debug(f"'{path}' file or directory exists.")
			return fileInfo

		logger.warning(f"'{path}' file or directory does not exists.")
		return False

	def createDirectory(self, path) -> bool:
		"""Creates the specified directory if it does not already exist.

		Args: 
			path (string): The path for the directory to be created.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		directory = qtc.QDir(path)
		if not directory.exists():
			directory.mkpath(directory.absolutePath())
			logger.info(f"Directory '{directory.absolutePath()}' was successfully created.")
		else:
			logger.debug(f"Directory '{directory.absolutePath()}' already exists.")

		return True

	def getFilesInDirectory(self,
		path,
		nameFilters=[],
		filters=qtc.QDir.Files,
		includeSubDirectories=qtc.QDirIterator.Subdirectories,
	) -> List[qtc.QFileInfo] or False:
		"""Returns a list with files contained in the specified directory.

		Args: 
			path (string): Path to the directory.
			nameFilters (list): A list with name filters e.g. ['ellie*'], ['*.fbx'].
			filters (QDir.Flag): NoFilter, Files.
			includeSubDirectories (QDirIterator.IteratorFlag): Whether or not search in
				sub-directories, Subdirectories - true, NoIteratorFlags - false.

		Returns:
			fileInfoList (List[QFileInfo] or False): List with QFileInfo objects that the
			directory contains,	if the list is empty or the directory does not exis it will
			return False.

		"""
		fileInfo = qtc.QFileInfo(path)
		if fileInfo.exists() and fileInfo.isDir():
			fileInfoList = []
			dirIter = qtc.QDirIterator(path, nameFilters, filters, includeSubDirectories)
			while dirIter.hasNext():
				dirIter.next()
				fileInfoList.append(dirIter.fileInfo())
		
			if len(fileInfoList) != 0:
				return fileInfoList
	
			logger.warning(f"'{path}' contains no files with those {nameFilters} name filters.")

		else:	logger.warning(f"Entry: '{path}' does not exist or is not a directory - nothing to return.")

		return False

	def copy(self, source, destination, overwrite=True) -> bool:
		"""Copies the source file / directory to the destination.

		Args:
			source (str): Source file or directory path.
			destination (str): Destination directory path.
			overwrite (bool): If destination file / directory exists, it will be overwritten.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		fileInfo = self.validateFileInfo(source)
		if not fileInfo: return False

		# Input can be a directory or a file
		finished = False
		if fileInfo.isDir():
			fileObjs = self.getFilesInDirectory(source)
			if len(fileObjs) != 0:
				for fileObj in fileObjs:
					destinationFilePath = fileObj.filePath().replace(source, destination)
					destinationFile = qtc.QFile(destinationFilePath)
					if overwrite and destinationFile.exists(): destinationFile.remove()

					destinationDir = qtc.QFileInfo(destinationFilePath).dir()
					self.createDirectory(destinationDir)
					finished = qtc.QFile(fileObj.filePath()).copy(destinationFilePath)
			else:
				logger.debug('Did not find any files to copy in the given directory')

		if fileInfo.isFile():
			self.createDirectory(destination)
			destinationFilePath = f'{destination}/{fileInfo.fileName()}'
			destinationFile = qtc.QFile(destinationFilePath)
			if overwrite and destinationFile.exists(): destinationFile.remove()
	
			finished = qtc.QFile(fileInfo.filePath()).copy(destinationFilePath)

		if finished:
			return True

		return False

	def copyInstallationFiles(self) -> None:
		"""Copies the installation files to the destination.
		
		Performs the actual installation by first copying the .mod file and then the
		moduleName folder with all its content.
		
		Returns: None

		"""
		self.copy(
			source=self.installationFiles[-1],
			destination=self.defaultModulePath
		)
		self.copy(
			source=f"{self.draggedFromPath}/{self.moduleName}",
			destination=f"{self.defaultModulePath}/{self.moduleName}"
		)

	def install(self) -> bool:
		"""Perform the actuall installation.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		TODO Create dialog input methods

		"""
		if not self.validatePythonVersion(): return False

		if not self.validateInstallationFiles(): return False

		input = self.createDialog(
			message=(
				f"This will install {self.moduleName} in:"
				f"\n{self.defaultModulePath}"
			),
			title=f"{self.moduleName} Installer"
		)
		if input == "Install":
			logger.info("PASSED : Ask user if installtion should proceed.")
			if self.installDependencies():

				self.removeExistingVersion()

				self.copyInstallationFiles()

				self.postInstallation()

				input = self.createDialog(
					message=(
						f"Installation complete - please restart Maya!"
					),
					title=f"{self.moduleName} Installer",
					buttons=["Restart", "Later"],
					cancelButton="Later"
				)
				if input == "Restart":
					logger.info("PASSED : Restarting Maya.")
					cmds.quit()
				else:
					logger.warning(f"PASSED : Successfully installed '{self.moduleName}' - please restart Maya!")

				return True
		else:
			logger.info(f"Installation of {self.moduleName} has been cancelled.")

		return False

	def postInstallation(self) -> None:
		"""Post installation procedures.

		Removes existing module entries from sys.path and sys.modules
		Appends the new module path to sys.path
		Reloads the newly installed module

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		self.removeModuleEntriesFromSys(self.moduleName)

		sys.path.append(self.moduleScriptPath)

		cmds.loadModule(scan=True)
		cmds.loadModule(allModules=True)

		basic.executeUserSetup()

	def removeModuleEntriesFromSys(self, moduleName) -> None:
		"""Removes all entries containing 'moduleName' from sys.path and sys.modules.

		Args:
			moduleName (str): Name of the module to be removed.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		for path in sys.path:
			if moduleName in path:
				sys.path.remove(path)
				logger.debug(f"'{moduleName}' was found and removed from sys.path entries.")
				break
		
		for module in sys.modules:
			if moduleName in module:
				sys.modules.pop(moduleName)
				logger.debug(f"'{moduleName}' was found and removed from sys.modules entries.")
				break

	def createDialog(self,
		message="Default Message",
		title="Default Title",
		icon="question",
		buttons=["Install", "Cancel"],
		cancelButton="Cancel"
	) -> str:
		"""Convinience wrapper method for creating confirm dialogs.

		Returns:
			str: Input from user as string e.g. "Install" or "Cancel".

		"""
		return cmds.confirmDialog(
			title=title,
			message=message,
			icon=icon,
			button=buttons,
			cancelButton=cancelButton,
			dismissString=cancelButton
		)



def onMayaDroppedPythonFile(*args, **kwargs):
	"""Main function that runs when dragging the file into Maya.

	Installation is performed by copying the module to the user preferences and creating
	a module file.

	"""
	DragDropInstall().install()