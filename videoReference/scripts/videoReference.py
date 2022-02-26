# Third-Party imports
try:
	import cv2
except ImportError:
	raise RuntimeError("opencv-python module could not be imported, is it installed?")

from maya import cmds
from maya import mel

import maya.OpenMaya as om
import maya.OpenMayaUI as omui



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
	_menuItems = []

	@classmethod
	def unhideCamera(cls, visibilityPlug) -> None:
		"""Unhides the given camera.

		If cameras transform has incoming connection a confirm dialog will pop up and ask
		whether or not you want to break them.

		This method uses OpenMaya with a DGModifier because it is capable of unlocking
		attributes that come from referenced files, but is not undoable.

		Args:
			visibilityPlug (MPlug): Visibilty plug for the camera to be unhidden

		"""
		if visibilityPlug.asBool() == 0 or visibilityPlug.isConnected():

			if visibilityPlug.isLocked():
				visibilityPlug.setLocked(False)

			if visibilityPlug.isConnected():
				input = cmds.confirmDialog(
					title="Visibility attribute on target camera has input connections!",
					message=f"""
						Camera: {cls._cameraTransform}
						has input connection on the visibility attribute which means that the movie
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
					print("// Incoming connection was broken! //")
				else:
					print("// Incoming connection was not broken and movie planes were still created. //")

			visibilityPlug.setBool(True)

			cls._dgMod.doIt()

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
	def createMoviePlane(cls, name, path, width, height, duration) -> None:
		"""Creates and sets up the image plane to work with video files.

		Args:
			name (string): Name of the image plane
			path (string): Path to the video file
			width (int): Width of the image plane
			height (int): Heigth of the image plane
			duration (int): End frame - total number of frames

		Returns:
			movieTransform (string): String representation of the movie transform node
			movieShape (string): String representation of the movie shape node

		"""
		cmds.imagePlane(
			name=name,
			lookThrough="persp",
			maintainRatio=True,
			width=width * 0.1,
			height=height * 0.1,
		)
		movieTransform = cmds.ls(selection=True)[0]
		movieShape = cmds.rename(
			cmds.listRelatives(movieTransform, allDescendents=True), f"{movieTransform}Shape"
		)

		cmds.setAttr(f"{movieShape}.type", 2)
		cmds.setAttr(f"{movieShape}.textureFilter", 1)
		cmds.setAttr(f"{movieShape}.useFrameExtension", True)
		cmds.setAttr(f"{movieShape}.imageName", path, type="string")
		cmds.delete(f"{movieShape}.frameExtension", inputConnectionsAndNodes=True)
		cmds.setAttr(f"{movieShape}.frameCache", duration)

		return movieTransform, movieShape

	@classmethod
	def keyVideoPlane(cls, movieShape, startFrame, endFrame) -> None:
		"""Sets linear keyframes on the given moviePlane frameExtension attribute.

		Args:
			movieShape (string): Name of the movie shape node
			startFrame (int): Starting frame
			endFrame (int): End frame - total length of the movie

		"""
		for frame in [startFrame, endFrame]:
			cmds.setKeyframe(
				movieShape,	attribute="frameExtension",
				time=frame, value=frame,
				inTangentType="linear", outTangentType="linear"
			)

	@classmethod
	def createTimeEditorClip(cls, name, startFrame, endFrame) -> None:
		"""Creates a time editor clip.

		Args:
			name (string): Name of the animation clip, it will be suffixed with _animClip
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
	def attatchToCamera(cls, movieTransform, scale=0.0025) -> None:
		"""Attach the movie plane to the camera.

		Args:
			movieTransform (string): Name of the movie transform node
			scale (float): Size of the movie plane

		"""
		cmds.parent(movieTransform, cls._cameraTransform)

		for attr in ["tx", "ty", "tz", "rx", "ry", "rz"]:
			cmds.setAttr(f"{movieTransform}.{attr}", 0)
		cmds.move(0, 0, -(cls._nearClip+1), movieTransform, os=True, r=True)

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
		moviePaths = cmds.fileDialog2(fileMode=4, dialogStyle=2, fileFilter=cls.videoFilters)

		if not moviePaths:
			print("// No movie file selected, operation aborted! //")
			return False
		else:
			cls.setupCamera()

			currentFrame = cmds.currentTime(query=True)

			if animClip:
				cls.setupTimeEditor()
				if openTimeEditor:
					cmds.TimeEditorWindow()

			for path in moviePaths:
				cap = cv2.VideoCapture(path)
				movie = path.split("/")[-1].split(".")[0]
				width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
				height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
				duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

				movieTransform, movieShape = cls.createMoviePlane(movie, path, width, height, duration)

				if animClip:
					cls.keyVideoPlane(movieShape, 1, duration)
					cls.createTimeEditorClip(movieTransform, currentFrame, duration)
				else:
					cls.keyVideoPlane(movieShape, currentFrame, duration)

				if attachToCamera:
					cls.attatchToCamera(movieTransform)

			cmds.select(clear=True)

			return True

	@classmethod
	def createVideoReference(cls, *args, **kwargs) -> None:
		"""Wrapper method for the main menu item."""
		cls.doIt()

	@classmethod
	def createMenuItems(cls) -> bool:
		"""Adds custom menu items in the maya main menu.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		if cls._menuItems:
			print("// Video Reference menu item already exists. //")
			return False

		menu = "mainCreateMenu"
		mel.eval("ModCreateMenu mainCreateMenu;")
		items = cmds.menu(menu, query=True, itemArray=True)
		measureItemIndex = None
		for index, item in enumerate(items):
			if item == "measureItem":
				measureItemIndex = index

		videoReferenceItem = cmds.menuItem(
			parent=menu,
			insertAfter=items[measureItemIndex-3],
			label="Video Reference",
			image="videoReference.png",
			command=cls.createVideoReference,
			sourceType="python",
		)
		cls._menuItems.append(videoReferenceItem)

		return True

	@classmethod
	def deleteMenuItems(cls) -> bool:
		"""Deletes custom menu items in the maya main menu.

		Returns:
			bool: True if the operation was successful, False if an	error occured during the
				operation.

		"""
		if len(cls._menuItems) == 0:
			print("// Video Reference menu item not found, nothing to delete. //")
			return False

		for item in cls._menuItems:
			cmds.deleteUI(item, menuItem=True)

		cls._menuItems.clear()

		return True
