# Third-Party imports
try:
	import cv2
except ImportError:
	raise RuntimeError("opencv-python module could not be imported, is it installed?")

# Built-in imports
import logging
from typing import Tuple

# Third-party imports
from maya import cmds
from maya import mel
import maya.OpenMaya as om
import maya.OpenMayaUI as omui



logger = logging.getLogger("VideoReference")



class VideoReference():

	"""Python module class for importing video references for animation."""

	videoFilters = """
		All Supported Video Formats ( .mp4 .mov .avi ) (*.mp4 *.mov *.avi);;
		Youtube and Vimeo ( .mp4 ) (*.mp4);;
		QuickTime ( .mov ) (*.mov);;
		Audio Video Interleave ( .avi ) (*.avi)
	"""
	_cameraTransform = None
	_nearClip = None
	_timeEditorComposition = None
	_dgMod = om.MDGModifier()

	# GUI
	_menuItems = []
	# Widgets
	_attachToCameraWidget = 'videoReferenceAttachToCamera'
	_animClipWidget = 'videoReferenceAnimClip'
	_openTimeEditorWidget = 'videoReferenceOpenTimeEditor'

	@classmethod
	def unhideCamera(cls, visibilityPlug) -> bool:
		"""Unhides the given camera.

		If cameras transform has incoming connection a confirm dialog will pop up and ask
		whether or not you want to break them.

		This method uses OpenMaya with a DGModifier because it is capable of unlocking
		attributes that come from referenced files, but it is not undoable.

		Args:
			visibilityPlug (MPlug): Visibilty plug for the camera to be unhidden

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		if visibilityPlug.asBool() == 0 or visibilityPlug.isConnected():

			if visibilityPlug.isLocked():	visibilityPlug.setLocked(False)

			if visibilityPlug.isConnected():
				input = cmds.confirmDialog(
					title="Visibility attribute on target camera has input connections!",
					message=f"""
						Camera: {cls._cameraTransform}
						has input connection on the visibility attribute which means that the video
						planes attached to it will disappear when the viewport updates.\n

						Visibilty on the target camera needs to be set to On, although disconnecting
						existing connections might break stuff.\n

						THIS OPERATION IS UNDOABLE!!!\n

						If You are not sure what You are doing it, is adviced NOT TO break existing
						connections.\n
					""",
					icon="warning",
					button=["Break", "Don't Break"],
					cancelButton="Don't Break",
				)
				if input == "Break":
					sourcePlug = visibilityPlug.source()
					cls._dgMod.disconnect(sourcePlug, visibilityPlug)
					logger.debug(f"Incoming connection was broken!")
				else:
					logger.debug("Incoming connection was not broken and video planes were still created.")

			visibilityPlug.setBool(True)

			cls._dgMod.doIt()

			return True

		return False


	@classmethod
	def setupCamera(cls) -> None:
		"""Sets up all internal attributes related to the camera.

		Internal call to the unhideCamera() class method is being invoked to check if the
		target camera is visible.

		"""
		cameraPath = om.MDagPath()
		omui.M3dView.active3dView().getCamera(cameraPath)
		cameraTransformFn = om.MFnDependencyNode(cameraPath.transform())

		cls._cameraTransform = cameraTransformFn.name()
		cls._nearClip = cmds.getAttr(f"{cameraPath.partialPathName()}.nearClipPlane")

		visibilityPlug = cameraTransformFn.findPlug("visibility")

		cls.unhideCamera(visibilityPlug)


	@classmethod
	def setupTimeEditor(cls) -> None:
		"""Checks if there are any time editor compositions in the scene.

		If there are no time editor composition present in the scene it will create
		Composition1, otherwise it will query the active composition.

		"""
		if not cmds.ls(type="timeEditorTracks"):
			cmds.timeEditorComposition("Composition1", createTrack=True)
		cls._timeEditorComposition = cmds.timeEditorComposition(query=True, active=True)


	@classmethod
	def createVideoPlane(cls, name, path, width, height, duration) -> Tuple[str, str]:
		"""Creates and sets up the image plane to work with video files.

		Args:
			name (str): Name of the image plane
			path (str): Path to the video file
			width (int): Width of the image plane
			height (int): Heigth of the image plane
			duration (int): End frame - total number of frames

		Returns:
			videoTransform (str): String representation of the video transform node
			videoShape (str): String representation of the video shape node

		"""
		cmds.imagePlane(
			name=name,
			lookThrough="persp",
			maintainRatio=True,
			width=width * 0.1,
			height=height * 0.1,
		)
		videoTransform = cmds.ls(selection=True)[0]
		videoShape = cmds.rename(
			cmds.listRelatives(videoTransform, allDescendents=True), f"{videoTransform}Shape"
		)

		cmds.setAttr(f"{videoShape}.type", 2)
		cmds.setAttr(f"{videoShape}.textureFilter", 1)
		cmds.setAttr(f"{videoShape}.useFrameExtension", True)
		cmds.setAttr(f"{videoShape}.imageName", path, type="string")
		cmds.delete(f"{videoShape}.frameExtension", inputConnectionsAndNodes=True)
		cmds.setAttr(f"{videoShape}.frameCache", duration)

		return videoTransform, videoShape


	@classmethod
	def keyVideoPlane(cls, videoShape, startFrame, endFrame) -> None:
		"""Sets linear keyframes on the given videoPlane frameExtension attribute.

		Args:
			videoShape (str): Name of the video shape node
			startFrame (int): Starting frame
			endFrame (int): End frame - total length of the video

		"""
		for frame in [startFrame, endFrame]:
			cmds.setKeyframe(
				videoShape,	attribute="frameExtension",
				time=frame, value=frame,
				inTangentType="linear", outTangentType="linear"
			)


	@classmethod
	def createTimeEditorClip(cls, name, startFrame, endFrame) -> None:
		"""Creates a time editor clip.

		Args:
			name (str): Name of the animation clip, it will be suffixed with _animClip
			startFrame (int): Starting frame of the animation clip
			endFrame (int): End frame - duration of the animation clip

		"""
		cmds.timeEditorClip(
			f"{name}_animClip",
			addSelectedObjects=True,
			recursively=True,
			removeSceneAnimation=True,
			startTime=startFrame,
			duration=endFrame,
			type=["animCurveTL", "animCurveTA", "animCurveTT", "animCurveTU"],
			track=f"{cls._timeEditorComposition}:-1"
		)


	@classmethod
	def attachToCamera(cls, videoTransform, scale=0.0025) -> None:
		"""Attach the video plane to the camera.

		Args:
			videoTransform (str): Name of the video transform node
			scale (float): Size of the video plane

		"""
		cmds.parent(videoTransform, cls._cameraTransform)

		for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
			cmds.setAttr(f"{videoTransform}.{attr}", 0)
		cmds.move(0, 0, -(cls._nearClip+1), videoTransform, os=True, r=True)

		cmds.scale(scale, scale, scale)


	@classmethod
	def doIt(cls, attachToCamera=True, animClip=True, openTimeEditor=True) -> bool:
		"""Main method for the 'command' doIt equivalent.

		Args:
			attachToCamera (bool): If True the video reference will be parented under the
				currently active camera.
			animCip (bool): If True a time editor clip will be created, otherwise only
				animation	curves will be placed.
			openTimeEditor (bool): If true a time editor window will be opened after import.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		videoPaths = cmds.fileDialog2(fileMode=4, dialogStyle=2, fileFilter=cls.videoFilters)

		if videoPaths:
			cls.setupCamera()

			currentFrame = cmds.currentTime(query=True)

			if animClip:
				cls.setupTimeEditor()
				if openTimeEditor:
					cmds.TimeEditorWindow()

			for path in videoPaths:
				cap = cv2.VideoCapture(path)
				video = path.split("/")[-1].split(".")[0]
				width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
				height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
				duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

				videoTransform, videoShape = cls.createVideoPlane(video, path, width, height, duration)

				if animClip:
					cls.keyVideoPlane(videoShape, 1, duration)
					cls.createTimeEditorClip(videoTransform, currentFrame, duration)
				else:
					cls.keyVideoPlane(videoShape, currentFrame, duration)

				if attachToCamera: cls.attachToCamera(videoTransform)

			cmds.select(clear=True)

			return True

		logger.info("No video file selected, operation aborted.")
		return False


	@classmethod
	def createVideoReference(cls, *args, **kwargs) -> bool:
		"""Wrapper method for the main menu item.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		kwargs = cls.getCreateCommandKwargs()
		if cls.doIt(**kwargs): return True

		return False


	@classmethod
	def displayOptionBox(cls, *args, **kwargs) -> None:
		"""Dipslays the option box window for the videoReference command."""

		layout = mel.eval('getOptionBox')
		cmds.setParent(layout)
		cmds.columnLayout(adjustableColumn=True)

		mel.eval('setOptionBoxTitle("Video Reference Options")')
		mel.eval('setOptionBoxCommandName("videoReference")')

		for widget in [cls._attachToCameraWidget, cls._animClipWidget, cls._openTimeEditorWidget]:
			try: cmds.deletUI(widget, control=True)
			except:	pass

		# Attach to Camera
		attachToCamera = cmds.optionVar(query=cls._attachToCameraWidget)
		cmds.checkBoxGrp(
			cls._attachToCameraWidget,
			label='Attach To Camera',
			numberOfCheckBoxes=1,
			value1=int(attachToCamera)
		)

		# Time Editor Clip
		animClip = cmds.optionVar(query=cls._animClipWidget)
		cmds.checkBoxGrp(
			cls._animClipWidget,
			label='Create Time Editor Clip',
			numberOfCheckBoxes=1,
			value1=int(animClip)
		)

		# Open Time Editor
		openTimeEditor = cmds.optionVar(query=cls._openTimeEditorWidget)
		cmds.checkBoxGrp(
			cls._openTimeEditorWidget,
			label='Open Time Editor',
			numberOfCheckBoxes=1,
			value1=int(openTimeEditor)
		)

		# Action Buttons
		applyAndCloseButton = mel.eval('getOptionBoxApplyAndCloseBtn')
		cmds.button(applyAndCloseButton, edit=True, command=cls.applyAndCloseButton)

		applyButton = mel.eval('getOptionBoxApplyBtn')
		cmds.button(applyButton, edit=True, command=cls.createVideoReference)

		closeButton = mel.eval('getOptionBoxCloseBtn')
		cmds.button(closeButton, edit=True, command=cls.closeOptionBox)

		# Buttons in the menu only accepts MEL
		resetButton = mel.eval('getOptionBoxResetBtn')
		cmds.button(resetButton, edit=True,
		 	command='python("from videoReference import VideoReference; VideoReference.resetToDefaults()")'
		)

		# Buttons in the menu only accepts MEL
		saveButton = mel.eval('getOptionBoxSaveBtn')
		cmds.button(saveButton,	edit=True,
		 	command='python("from videoReference import VideoReference; VideoReference.getCreateCommandKwargs()")'
		)

		mel.eval('showOptionBox')


	@classmethod
	def applyAndCloseButton(cls, *args, **kwargs) -> None:
		"""Calls the createVideoReference method and closes the option box window. """
		cls.createVideoReference()
		mel.eval('saveOptionBoxSize')


	@classmethod
	def resetToDefaults(cls, *args, **kwargs) -> None:
		"""Resets the settings to default ones."""
		cmds.checkBoxGrp(cls._attachToCameraWidget, edit=True, value1=True)
		cmds.checkBoxGrp(cls._animClipWidget, edit=True, value1=True)
		cmds.checkBoxGrp(cls._openTimeEditorWidget, edit=True, value1=True)


	@classmethod
	def getCreateCommandKwargs(cls, *args, **kwargs) -> dict:
		"""Gets the videoReference command arguments.

		The arguments are queried eiter from the option box widgets or the saved option
		variables. If the widgets exist, their values will be saved to the option variables.

		Returns:
			dict: Dictionary of the kwargs to the videoReference command.

		"""
		args = {}

		# Attach to Camera
		if cmds.checkBoxGrp(cls._attachToCameraWidget, exists=True):
			if cmds.checkBoxGrp(cls._attachToCameraWidget, query=True, value1=True):
				args['attachToCamera'] = True
				cmds.optionVar(intValue=(cls._attachToCameraWidget, 1))
			else:
				args['attachToCamera'] = False
				cmds.optionVar(intValue=(cls._attachToCameraWidget, 0))
		else:
			value = cmds.optionVar(query=cls._attachToCameraWidget)
			if value:
				args['attachToCamera'] = True

		# Create Time Editor Clip
		if cmds.checkBoxGrp(cls._animClipWidget, exists=True):
			if cmds.checkBoxGrp(cls._animClipWidget, query=True, value1=True):
				args['animClip'] = True
				cmds.optionVar(intValue=(cls._animClipWidget, 1))
			else:
				args['animClip'] = False
				cmds.optionVar(intValue=(cls._animClipWidget, 0))
		else:
			value = cmds.optionVar(query=cls._animClipWidget)
			if value:
				args['animClip'] = True

		# Open Time Editor
		if cmds.checkBoxGrp(cls._openTimeEditorWidget, exists=True):
			if cmds.checkBoxGrp(cls._openTimeEditorWidget, query=True, value1=True):
				args['openTimeEditor'] = True
				cmds.optionVar(intValue=(cls._openTimeEditorWidget, 1))
			else:
				args['openTimeEditor'] = False
				cmds.optionVar(intValue=(cls._openTimeEditorWidget, 0))
		else:
			value = cmds.optionVar(query=cls._openTimeEditorWidget)
			if value:
				args['openTimeEditor'] = True

		return args


	@classmethod
	def closeOptionBox(cls, *args, **kwargs) -> None:
		"""Closes the option box window."""
		mel.eval('hideOptionBox')


	@classmethod
	def createMenuItems(cls) -> bool:
		"""Adds custom menu items in the maya main menu.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		if len(cls._menuItems) == 0:
			menu = "mainCreateMenu"
			mel.eval("ModCreateMenu mainCreateMenu;")
			items = cmds.menu(menu, query=True, itemArray=True)
			measureItemIndex = None
			for index, item in enumerate(items):
				if item == "measureItem":	measureItemIndex = index

			# Video Reference
			videoReferenceItem = cmds.menuItem(
				parent=menu,
				insertAfter=items[measureItemIndex-3],
				label="Video Reference",
				image="videoReference.png",
				command=cls.createVideoReference,
				sourceType="python",
			)

			# Video Reference Option Box
			videoReferenceOptBox = cmds.menuItem(
				parent=menu,
				insertAfter=videoReferenceItem,
				command=cls.displayOptionBox,
				optionBox=True,
			)

			cls._menuItems.append(videoReferenceItem)
			cls._menuItems.append(videoReferenceOptBox)

			return True

		logger.debug("'Video Reference' menu item already exists.")
		return False


	@classmethod
	def deleteMenuItems(cls) -> bool:
		"""Deletes custom menu items in the maya main menu.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		if len(cls._menuItems) != 0:
			for item in cls._menuItems:
				cmds.deleteUI(item, menuItem=True)

			cls._menuItems.clear()

			logger.debug("Successfully deleted 'Video Reference' menu item from main Create Menu.")
			return True

		logger.debug("'Video Reference' menu item not found, nothing to delete.")
		return False
