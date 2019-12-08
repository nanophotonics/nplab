from __future__ import print_function
def transpose_dictionary(dictionary):
	keys = list(dictionary.keys())
	values = list(dictionary.values())
	assert(len(set(values))==len(values)) #assert values are unique
	output = {}
	for k,v in list(dictionary.items()):
		output.update({v:k})
	return output 

def PI_V(value_type,constraint_type,parameter_index):

	''' Perform bitshift operations for to encode into binary the parameter, it's type info + constraint''' 

	v = transpose_dictionary(PicamValueType)[value_type]
	c = transpose_dictionary(PicamConstraintType)[constraint_type]
	n = int(parameter_index)
	return (((c)<<24)+((v)<<16)+(n))

PicamParameter={
	"PicamParameter_SensorActiveWidth":('PicamValueType_Integer','PicamConstraintType_None',59),
	"PicamParameter_ModulationOutputSignalFrequency":('PicamValueType_FloatingPoint','PicamConstraintType_Range',117),
	"PicamParameter_Accumulations":('PicamValueType_LargeInteger','PicamConstraintType_Range',92),
	"PicamParameter_SensorActiveLeftMargin":('PicamValueType_Integer','PicamConstraintType_None',61),
	"PicamParameter_ExternalShutterType":('PicamValueType_Enumeration','PicamConstraintType_None',152),
	"PicamParameter_CustomModulationSequence":('PicamValueType_Modulations','PicamConstraintType_Modulations',119),
	"PicamParameter_CleanUntilTrigger":('PicamValueType_Boolean','PicamConstraintType_Collection',22),
	"PicamParameter_PhotocathodeSensitivity":('PicamValueType_Enumeration','PicamConstraintType_None',107),
	"PicamParameter_ShutterClosingDelay":('PicamValueType_FloatingPoint','PicamConstraintType_Range',25),
	"PicamParameter_InternalShutterStatus":('PicamValueType_Enumeration','PicamConstraintType_None',153),
	"PicamParameter_EnableAuxOutput":('PicamValueType_Boolean','PicamConstraintType_Collection',161),
	"PicamParameter_KineticsWindowHeight":('PicamValueType_Integer','PicamConstraintType_Range',56),
	"PicamParameter_DelayFromPreTrigger":('PicamValueType_FloatingPoint','PicamConstraintType_Range',132),
	"PicamParameter_GatingSpeed":('PicamValueType_Enumeration','PicamConstraintType_None',108),
	"PicamParameter_ExternalShutterStatus":('PicamValueType_Enumeration','PicamConstraintType_None',154),
	"PicamParameter_SensorSecondaryActiveHeight":('PicamValueType_Integer','PicamConstraintType_None',74),
	"PicamParameter_ExactReadoutCountMaximum":('PicamValueType_LargeInteger','PicamConstraintType_None',77),
	"PicamParameter_AdcSpeed":('PicamValueType_FloatingPoint','PicamConstraintType_Collection',33),
	"PicamParameter_PhosphorType":('PicamValueType_Enumeration','PicamConstraintType_None',109),
	"PicamParameter_SensorActiveRightMargin":('PicamValueType_Integer','PicamConstraintType_None',63),
	"PicamParameter_CorrectPixelBias":('PicamValueType_Boolean','PicamConstraintType_Collection',106),
	"PicamParameter_CenterWavelengthReading":('PicamValueType_FloatingPoint','PicamConstraintType_None',141),
	"PicamParameter_CleanBeforeExposure":('PicamValueType_Boolean','PicamConstraintType_Collection',78),
	"PicamParameter_TriggerSource":('PicamValueType_Enumeration','PicamConstraintType_Collection',79),
	"PicamParameter_OutputSignal2":('PicamValueType_Enumeration','PicamConstraintType_Collection',150),
	"PicamParameter_SensorActiveTopMargin":('PicamValueType_Integer','PicamConstraintType_None',62),
	"PicamParameter_InactiveShutterTimingModeResult":('PicamValueType_Enumeration','PicamConstraintType_None',156),
	"PicamParameter_ActiveBottomMargin":('PicamValueType_Integer','PicamConstraintType_Range',6),
	"PicamParameter_AdcEMGain":('PicamValueType_Integer','PicamConstraintType_Range',53),
	"PicamParameter_ShutterDelayResolution":('PicamValueType_FloatingPoint','PicamConstraintType_Collection',47),
	"PicamParameter_Orientation":('PicamValueType_Enumeration','PicamConstraintType_None',38),
	"PicamParameter_LaserStatus":('PicamValueType_Enumeration','PicamConstraintType_None',157),
	"PicamParameter_SensorActiveHeight":('PicamValueType_Integer','PicamConstraintType_None',60),
	"PicamParameter_EnableModulation":('PicamValueType_Boolean','PicamConstraintType_Collection',111),
	"PicamParameter_Rois,":('PicamValueType_Rois','PicamConstraintType_Rois',37),
	"PicamParameter_CleanSerialRegister":('PicamValueType_Boolean','PicamConstraintType_Collection',19),
	"PicamParameter_NondestructiveReadoutPeriod":('PicamValueType_FloatingPoint','PicamConstraintType_Range',129),
	"PicamParameter_EnableNondestructiveReadout":('PicamValueType_Boolean','PicamConstraintType_Collection',128),
	"PicamParameter_TriggerDelay":('PicamValueType_FloatingPoint','PicamConstraintType_Range',164),
	"PicamParameter_ReadoutTimeCalculation":('PicamValueType_FloatingPoint','PicamConstraintType_None',27),
	"PicamParameter_TriggerFrequency":('PicamValueType_FloatingPoint','PicamConstraintType_Range',80),
	"PicamParameter_ShutterTimingMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',24),
	"PicamParameter_IntensifierStatus":('PicamValueType_Enumeration','PicamConstraintType_None',87),
	"PicamParameter_InvertOutputSignal":('PicamValueType_Boolean','PicamConstraintType_Collection',52),
	"PicamParameter_OnlineReadoutRateCalculation":('PicamValueType_FloatingPoint','PicamConstraintType_None',99),
	"PicamParameter_SecondaryActiveHeight":('PicamValueType_Integer','PicamConstraintType_Range',76),
	"PicamParameter_SensorSecondaryMaskedHeight":('PicamValueType_Integer','PicamConstraintType_None',49),
	"PicamParameter_LightSourceStatus":('PicamValueType_Enumeration','PicamConstraintType_None',134),
	"PicamParameter_SensorMaskedBottomMargin":('PicamValueType_Integer','PicamConstraintType_None',67),
	"PicamParameter_ModulationOutputSignalAmplitude":('PicamValueType_FloatingPoint','PicamConstraintType_Range',120),
	"PicamParameter_DisableDataFormatting":('PicamValueType_Boolean','PicamConstraintType_Collection',55),
	"PicamParameter_SecondaryMaskedHeight":('PicamValueType_Integer','PicamConstraintType_Range',75),
	"PicamParameter_PixelBitDepth":('PicamValueType_Integer','PicamConstraintType_None',48),
	"PicamParameter_ReadoutControlMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',26),
	"PicamParameter_SensorMaskedTopMargin":('PicamValueType_Integer','PicamConstraintType_None',66),
	"PicamParameter_SensorTemperatureStatus":('PicamValueType_Enumeration','PicamConstraintType_None',16),
	"PicamParameter_DifStartingGate":('PicamValueType_Pulse','PicamConstraintType_Pulse',102),
	"PicamParameter_ExposureTime":('PicamValueType_FloatingPoint','PicamConstraintType_Range',23),
	"PicamParameter_ReadoutCount":('PicamValueType_LargeInteger','PicamConstraintType_Range',40),
	"PicamParameter_SensorMaskedHeight":('PicamValueType_Integer','PicamConstraintType_None',65),
	"PicamParameter_CleanSectionFinalHeight":('PicamValueType_Integer','PicamConstraintType_Range',17),
	"PicamParameter_StopCleaningOnPreTrigger":('PicamValueType_Boolean','PicamConstraintType_Collection',130),
	"PicamParameter_DifEndingGate":('PicamValueType_Pulse','PicamConstraintType_Pulse',103),
	"PicamParameter_MaskedBottomMargin":('PicamValueType_Integer','PicamConstraintType_Range',73),
	"PicamParameter_CleanSectionFinalHeightCount":('PicamValueType_Integer','PicamConstraintType_Range',18),
	"PicamParameter_SensorActiveBottomMargin":('PicamValueType_Integer','PicamConstraintType_None',64),
	"PicamParameter_LifeExpectancy":('PicamValueType_FloatingPoint','PicamConstraintType_None',136),
	"PicamParameter_ActiveExtendedHeight":('PicamValueType_Integer','PicamConstraintType_Range',160),
	"PicamParameter_TimeStampResolution":('PicamValueType_LargeInteger','PicamConstraintType_Collection',69),
	"PicamParameter_TimeStampBitDepth":('PicamValueType_Integer','PicamConstraintType_Collection',70),
	"PicamParameter_GratingGrooveDensity":('PicamValueType_FloatingPoint','PicamConstraintType_None',144),
	"PicamParameter_GateTrackingBitDepth":('PicamValueType_Integer','PicamConstraintType_Collection',105),
	"PicamParameter_AdcBitDepth":('PicamValueType_Integer','PicamConstraintType_Collection',34),
	"PicamParameter_ReadoutPortCount":('PicamValueType_Integer','PicamConstraintType_Collection',28),
	"PicamParameter_LaserPower":('PicamValueType_FloatingPoint','PicamConstraintType_Range',138),
	"PicamParameter_TriggerResponse":('PicamValueType_Enumeration','PicamConstraintType_Collection',30),
	"PicamParameter_CleanCycleHeight":('PicamValueType_Integer','PicamConstraintType_Range',21),
	"PicamParameter_VacuumStatus":('PicamValueType_Enumeration','PicamConstraintType_None',165),
	"PicamParameter_FrameStride":('PicamValueType_Integer','PicamConstraintType_None',43),
	"PicamParameter_TriggerDetermination":('PicamValueType_Enumeration','PicamConstraintType_Collection',31),
	"PicamParameter_ShutterOpeningDelay":('PicamValueType_FloatingPoint','PicamConstraintType_Range',46),
	"PicamParameter_EMIccdGainControlMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',123),
	"PicamParameter_EnableSyncMaster":('PicamValueType_Boolean','PicamConstraintType_Collection',84),
	"PicamParameter_ActiveTopMargin":('PicamValueType_Integer','PicamConstraintType_Range',4),
	"PicamParameter_PhosphorDecayDelayResolution":('PicamValueType_FloatingPoint','PicamConstraintType_Collection',90),
	"PicamParameter_SensorActiveExtendedHeight":('PicamValueType_Integer','PicamConstraintType_None',159),
	"PicamParameter_AnticipateTrigger":('PicamValueType_Boolean','PicamConstraintType_Collection',131),
	"PicamParameter_SensorAngle":('PicamValueType_FloatingPoint','PicamConstraintType_None',148),
	"PicamParameter_EnableModulationOutputSignal":('PicamValueType_Boolean','PicamConstraintType_Collection',116),
	"PicamParameter_MaskedHeight":('PicamValueType_Integer','PicamConstraintType_Range',7),
	"PicamParameter_RepetitiveGate":('PicamValueType_Pulse','PicamConstraintType_Pulse',94),
	"PicamParameter_CenterWavelengthSetPoint":('PicamValueType_FloatingPoint','PicamConstraintType_Range',140),
	"PicamParameter_FrameTrackingBitDepth":('PicamValueType_Integer','PicamConstraintType_Collection',72),
	"PicamParameter_CoolingFanStatus":('PicamValueType_Enumeration','PicamConstraintType_None',162),
	"PicamParameter_VerticalShiftRate":('PicamValueType_FloatingPoint','PicamConstraintType_Collection',13),
	"PicamParameter_SensorTemperatureReading":('PicamValueType_FloatingPoint','PicamConstraintType_None',15),
	"PicamParameter_SequentialStartingGate":('PicamValueType_Pulse','PicamConstraintType_Pulse',95),
	"PicamParameter_SensorTemperatureSetPoint":('PicamValueType_FloatingPoint','PicamConstraintType_Range',14),
	"PicamParameter_FrameRateCalculation":('PicamValueType_FloatingPoint','PicamConstraintType_None',51),
	"PicamParameter_PixelFormat":('PicamValueType_Enumeration','PicamConstraintType_Collection',41),
	"PicamParameter_ModulationFrequency":('PicamValueType_FloatingPoint','PicamConstraintType_Range',112),
	"PicamParameter_ReadoutOrientation":('PicamValueType_Enumeration','PicamConstraintType_None',54),
	"PicamParameter_ReadoutRateCalculation":('PicamValueType_FloatingPoint','PicamConstraintType_None',50),
	"PicamParameter_FramesPerReadout":('PicamValueType_Integer','PicamConstraintType_None',44),
	"PicamParameter_GatingMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',93),
	"PicamParameter_GratingType":('PicamValueType_Enumeration','PicamConstraintType_None',142),
	"PicamParameter_PixelGapHeight":('PicamValueType_FloatingPoint','PicamConstraintType_None',12),
	"PicamParameter_ReadoutStride":('PicamValueType_Integer','PicamConstraintType_None',45),
	"PicamParameter_SequentialGateStepCount":('PicamValueType_LargeInteger','PicamConstraintType_Range',97),
	"PicamParameter_SeNsRWindowHeight":('PicamValueType_Integer','PicamConstraintType_Range',163),
	"PicamParameter_FocalLength":('PicamValueType_FloatingPoint','PicamConstraintType_None',146),
	"PicamParameter_PixelGapWidth":('PicamValueType_FloatingPoint','PicamConstraintType_None',11),
	"PicamParameter_InternalShutterType":('PicamValueType_Enumeration','PicamConstraintType_None',139),
	"PicamParameter_SensorType":('PicamValueType_Enumeration','PicamConstraintType_None',57),
	"PicamParameter_EnableIntensifier":('PicamValueType_Boolean','PicamConstraintType_Collection',86),
	"PicamParameter_PixelHeight":('PicamValueType_FloatingPoint','PicamConstraintType_None',10),
	"PicamParameter_TrackFrames":('PicamValueType_Boolean','PicamConstraintType_Collection',71),
	"PicamParameter_EMIccdGain":('PicamValueType_Integer','PicamConstraintType_Range',124),
	"PicamParameter_CcdCharacteristics":('PicamValueType_Enumeration','PicamConstraintType_None',58),
	"PicamParameter_NormalizeOrientation":('PicamValueType_Boolean','PicamConstraintType_Collection',39),
	"PicamParameter_Age":('PicamValueType_FloatingPoint','PicamConstraintType_None',135),
	"PicamParameter_SequentialGateStepIterations":('PicamValueType_LargeInteger','PicamConstraintType_Range',98),
	"PicamParameter_TriggerTermination":('PicamValueType_Enumeration','PicamConstraintType_Collection',81),
	"PicamParameter_ActiveRightMargin":('PicamValueType_Integer','PicamConstraintType_Range',5),
	"PicamParameter_GratingCoating":('PicamValueType_Enumeration','PicamConstraintType_None',143),
	"PicamParameter_EnableSensorWindowHeater":('PicamValueType_Boolean','PicamConstraintType_Collection',127),
	"PicamParameter_PhotonDetectionThreshold":('PicamValueType_FloatingPoint','PicamConstraintType_Range',126),
	"PicamParameter_ActiveLeftMargin":('PicamValueType_Integer','PicamConstraintType_Range',3),
	"PicamParameter_InputTriggerStatus":('PicamValueType_Enumeration','PicamConstraintType_None',158),
	"PicamParameter_TriggerCoupling":('PicamValueType_Enumeration','PicamConstraintType_Collection',82),
	"PicamParameter_LaserOutputMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',137),
	"PicamParameter_OutputSignal":('PicamValueType_Enumeration','PicamConstraintType_Collection',32),
	"PicamParameter_AuxOutput":('PicamValueType_Pulse','PicamConstraintType_Pulse',91),
	"PicamParameter_TimeStamps":('PicamValueType_Enumeration','PicamConstraintType_Collection',68),
	"PicamParameter_ActiveHeight":('PicamValueType_Integer','PicamConstraintType_Range',2),
	"PicamParameter_ModulationTracking":('PicamValueType_Enumeration','PicamConstraintType_Collection',121),
	"PicamParameter_PhosphorDecayDelay":('PicamValueType_FloatingPoint','PicamConstraintType_Range',89),
	"PicamParameter_ModulationTrackingBitDepth":('PicamValueType_Integer','PicamConstraintType_Collection',122),
	"PicamParameter_GateTracking":('PicamValueType_Enumeration','PicamConstraintType_Collection',104),
	"PicamParameter_MaskedTopMargin":('PicamValueType_Integer','PicamConstraintType_Range',8),
	"PicamParameter_ActiveWidth":('PicamValueType_Integer','PicamConstraintType_Range',1),
	"PicamParameter_InclusionAngle":('PicamValueType_FloatingPoint','PicamConstraintType_None',147),
	"PicamParameter_ActiveShutter":('PicamValueType_Enumeration','PicamConstraintType_Collection',155),
	"PicamParameter_LightSource":('PicamValueType_Enumeration','PicamConstraintType_Collection',133),
	"PicamParameter_SyncMaster2Delay":('PicamValueType_FloatingPoint','PicamConstraintType_Range',85),
	"PicamParameter_SequentialEndingModulationPhase":('PicamValueType_FloatingPoint','PicamConstraintType_Range',115),
	"PicamParameter_CleanCycleCount":('PicamValueType_Integer','PicamConstraintType_Range',20),
	"PicamParameter_AdcAnalogGain":('PicamValueType_Enumeration','PicamConstraintType_Collection',35),
	"PicamParameter_SequentialStartingModulationPhase":('PicamValueType_FloatingPoint','PicamConstraintType_Range',114),
	"PicamParameter_PixelWidth":('PicamValueType_FloatingPoint','PicamConstraintType_None',9),
	"PicamParameter_DisableCoolingFan":('PicamValueType_Boolean','PicamConstraintType_Collection',29),
	"PicamParameter_IntensifierOptions":('PicamValueType_Enumeration','PicamConstraintType_None',101),
	"PicamParameter_AdcQuality":('PicamValueType_Enumeration','PicamConstraintType_Collection',36),
	"PicamParameter_RepetitiveModulationPhase":('PicamValueType_FloatingPoint','PicamConstraintType_Range',113),
	"PicamParameter_FrameSize":('PicamValueType_Integer','PicamConstraintType_None',42),
	"PicamParameter_InvertOutputSignal2":('PicamValueType_Boolean','PicamConstraintType_Collection',151),
	"PicamParameter_PhotonDetectionMode":('PicamValueType_Enumeration','PicamConstraintType_Collection',125),
	"PicamParameter_ModulationDuration":('PicamValueType_FloatingPoint','PicamConstraintType_Range',118),
	"PicamParameter_IntensifierGain":('PicamValueType_Integer','PicamConstraintType_Range',88),
	"PicamParameter_BracketGating":('PicamValueType_Boolean','PicamConstraintType_Collection',100),
	"PicamParameter_GratingBlazingWavelength":('PicamValueType_FloatingPoint','PicamConstraintType_None',145),
	"PicamParameter_IntensifierDiameter":('PicamValueType_FloatingPoint','PicamConstraintType_None',110),
	"PicamParameter_TriggerThreshold":('PicamValueType_FloatingPoint','PicamConstraintType_Range',83),
	"PicamParameter_CenterWavelengthStatus":('PicamValueType_Enumeration','PicamConstraintType_None',149),
	"PicamParameter_SequentialEndingGate":('PicamValueType_Pulse','PicamConstraintType_Pulse',96)
}


PicamError = {
	0 :"PicamError_None",
	4 :"PicamError_UnexpectedError",
	3 :"PicamError_UnexpectedNullPointer",
	35 :"PicamError_InvalidPointer",
	39 :"PicamError_InvalidCount",
	42 :"PicamError_InvalidOperation",
	43 :"PicamError_OperationCanceled",
	1 :"PicamError_LibraryNotInitialized",
	5 :"PicamError_LibraryAlreadyInitialized",
	16 :"PicamError_InvalidEnumeratedType",
	17 :"PicamError_EnumerationValueNotDefined",
	18 :"PicamError_NotDiscoveringCameras",
	19 :"PicamError_AlreadyDiscoveringCameras",
	48 :"PicamError_NotDiscoveringAccessories",
	49 :"PicamError_AlreadyDiscoveringAccessories",
	34 :"PicamError_NoCamerasAvailable",
	7 :"PicamError_CameraAlreadyOpened",
	8 :"PicamError_InvalidCameraID",
	45 :"PicamError_NoAccessoriesAvailable",
	46 :"PicamError_AccessoryAlreadyOpened",
	47 :"PicamError_InvalidAccessoryID",
	9 :"PicamError_InvalidHandle",
	15 :"PicamError_DeviceCommunicationFailed",
	23 :"PicamError_DeviceDisconnected",
	24 :"PicamError_DeviceOpenElsewhere",
	6 :"PicamError_InvalidDemoModel",
	21 :"PicamError_InvalidDemoSerialNumber",
	22 :"PicamError_DemoAlreadyConnected",
	40 :"PicamError_DemoNotSupported",
	11 :"PicamError_ParameterHasInvalidValueType",
	13 :"PicamError_ParameterHasInvalidConstraintType",
	12 :"PicamError_ParameterDoesNotExist",
	10 :"PicamError_ParameterValueIsReadOnly",
	2 :"PicamError_InvalidParameterValue",
	38 :"PicamError_InvalidConstraintCategory",
	14 :"PicamError_ParameterValueIsIrrelevant",
	25 :"PicamError_ParameterIsNotOnlineable",
	26 :"PicamError_ParameterIsNotReadable",
	50 :"PicamError_ParameterIsNotWaitableStatus",
	51 :"PicamError_InvalidWaitableStatusParameterTimeOut",
	28 :"PicamError_InvalidParameterValues",
	29 :"PicamError_ParametersNotCommitted",
	30 :"PicamError_InvalidAcquisitionBuffer",
	36 :"PicamError_InvalidReadoutCount",
	37 :"PicamError_InvalidReadoutTimeOut",
	31 :"PicamError_InsufficientMemory",
	20 :"PicamError_AcquisitionInProgress",
	27 :"PicamError_AcquisitionNotInProgress",
	32 :"PicamError_TimeOutOccurred",
	33 :"PicamError_AcquisitionUpdatedHandlerRegistered",
	44 :"PicamError_InvalidAcquisitionState",
	41 :"PicamError_NondestructiveReadoutEnabled",
	52 :"PicamError_ShutterOverheated",
	54 :"PicamError_CenterWavelengthFaulted",
	53 :"PicamError_CameraFaulted"
}

PicamEnumeratedType = {
	1 :"PicamEnumeratedType_Error",
	29 :"PicamEnumeratedType_EnumeratedType",
	2 :"PicamEnumeratedType_Model",
	3 :"PicamEnumeratedType_ComputerInterface",
	26 :"PicamEnumeratedType_DiscoveryAction",
	27 :"PicamEnumeratedType_HandleType",
	4 :"PicamEnumeratedType_ValueType",
	5 :"PicamEnumeratedType_ConstraintType",
	6 :"PicamEnumeratedType_Parameter",
	53 :"PicamEnumeratedType_ActiveShutter",
	7 :"PicamEnumeratedType_AdcAnalogGain",
	8 :"PicamEnumeratedType_AdcQuality",
	9 :"PicamEnumeratedType_CcdCharacteristicsMask",
	51 :"PicamEnumeratedType_CenterWavelengthStatus",
	56 :"PicamEnumeratedType_CoolingFanStatus",
	42 :"PicamEnumeratedType_EMIccdGainControlMode",
	36 :"PicamEnumeratedType_GateTrackingMask",
	34 :"PicamEnumeratedType_GatingMode",
	38 :"PicamEnumeratedType_GatingSpeed",
	48 :"PicamEnumeratedType_GratingCoating",
	49 :"PicamEnumeratedType_GratingType",
	35 :"PicamEnumeratedType_IntensifierOptionsMask",
	33 :"PicamEnumeratedType_IntensifierStatus",
	45 :"PicamEnumeratedType_LaserOutputMode",
	54 :"PicamEnumeratedType_LaserStatus",
	46 :"PicamEnumeratedType_LightSource",
	47 :"PicamEnumeratedType_LightSourceStatus",
	41 :"PicamEnumeratedType_ModulationTrackingMask",
	10 :"PicamEnumeratedType_OrientationMask",
	11 :"PicamEnumeratedType_OutputSignal",
	39 :"PicamEnumeratedType_PhosphorType",
	40 :"PicamEnumeratedType_PhotocathodeSensitivity",
	43 :"PicamEnumeratedType_PhotonDetectionMode",
	12 :"PicamEnumeratedType_PixelFormat",
	13 :"PicamEnumeratedType_ReadoutControlMode",
	14 :"PicamEnumeratedType_SensorTemperatureStatus",
	15 :"PicamEnumeratedType_SensorType",
	52 :"PicamEnumeratedType_ShutterStatus",
	16 :"PicamEnumeratedType_ShutterTimingMode",
	50 :"PicamEnumeratedType_ShutterType",
	17 :"PicamEnumeratedType_TimeStampsMask",
	30 :"PicamEnumeratedType_TriggerCoupling",
	18 :"PicamEnumeratedType_TriggerDetermination",
	19 :"PicamEnumeratedType_TriggerResponse",
	31 :"PicamEnumeratedType_TriggerSource",
	55 :"PicamEnumeratedType_TriggerStatus",
	32 :"PicamEnumeratedType_TriggerTermination",
	57 :"PicamEnumeratedType_VacuumStatus",
	20 :"PicamEnumeratedType_ValueAccess",
	28 :"PicamEnumeratedType_DynamicsMask",
	21 :"PicamEnumeratedType_ConstraintScope",
	22 :"PicamEnumeratedType_ConstraintSeverity",
	23 :"PicamEnumeratedType_ConstraintCategory",
	24 :"PicamEnumeratedType_RoisConstraintRulesMask",
	25 :"PicamEnumeratedType_AcquisitionErrorsMask",
	37 :"PicamEnumeratedType_AcquisitionState",
	44 :"PicamEnumeratedType_AcquisitionStateErrorsMask"
}

PicamModel = {
	1400 :"PicamModel_PIMteSeries",
	1401 :"PicamModel_PIMte1024Series",
	1402 :"PicamModel_PIMte1024F",
	1403 :"PicamModel_PIMte1024B",
	1405 :"PicamModel_PIMte1024BR",
	1404 :"PicamModel_PIMte1024BUV",
	1406 :"PicamModel_PIMte1024FTSeries",
	1407 :"PicamModel_PIMte1024FT",
	1408 :"PicamModel_PIMte1024BFT",
	1412 :"PicamModel_PIMte1300Series",
	1413 :"PicamModel_PIMte1300B",
	1414 :"PicamModel_PIMte1300R",
	1415 :"PicamModel_PIMte1300BR",
	1416 :"PicamModel_PIMte2048Series",
	1417 :"PicamModel_PIMte2048B",
	1418 :"PicamModel_PIMte2048BR",
	1409 :"PicamModel_PIMte2KSeries",
	1410 :"PicamModel_PIMte2KB",
	1411 :"PicamModel_PIMte2KBUV",
	2000 :"PicamModel_PIMte3Series",
	2001 :"PicamModel_PIMte32048Series",
	2002 :"PicamModel_PIMte32048B",
	0 :"PicamModel_PixisSeries",
	1 :"PicamModel_Pixis100Series",
	2 :"PicamModel_Pixis100F",
	6 :"PicamModel_Pixis100B",
	3 :"PicamModel_Pixis100R",
	4 :"PicamModel_Pixis100C",
	5 :"PicamModel_Pixis100BR",
	54 :"PicamModel_Pixis100BExcelon",
	55 :"PicamModel_Pixis100BRExcelon",
	7 :"PicamModel_PixisXO100B",
	8 :"PicamModel_PixisXO100BR",
	68 :"PicamModel_PixisXB100B",
	69 :"PicamModel_PixisXB100BR",
	26 :"PicamModel_Pixis256Series",
	27 :"PicamModel_Pixis256F",
	29 :"PicamModel_Pixis256B",
	28 :"PicamModel_Pixis256E",
	30 :"PicamModel_Pixis256BR",
	31 :"PicamModel_PixisXB256BR",
	37 :"PicamModel_Pixis400Series",
	38 :"PicamModel_Pixis400F",
	40 :"PicamModel_Pixis400B",
	39 :"PicamModel_Pixis400R",
	41 :"PicamModel_Pixis400BR",
	56 :"PicamModel_Pixis400BExcelon",
	57 :"PicamModel_Pixis400BRExcelon",
	42 :"PicamModel_PixisXO400B",
	70 :"PicamModel_PixisXB400BR",
	43 :"PicamModel_Pixis512Series",
	44 :"PicamModel_Pixis512F",
	45 :"PicamModel_Pixis512B",
	46 :"PicamModel_Pixis512BUV",
	58 :"PicamModel_Pixis512BExcelon",
	49 :"PicamModel_PixisXO512F",
	50 :"PicamModel_PixisXO512B",
	48 :"PicamModel_PixisXF512F",
	47 :"PicamModel_PixisXF512B",
	9 :"PicamModel_Pixis1024Series",
	10 :"PicamModel_Pixis1024F",
	11 :"PicamModel_Pixis1024B",
	13 :"PicamModel_Pixis1024BR",
	12 :"PicamModel_Pixis1024BUV",
	59 :"PicamModel_Pixis1024BExcelon",
	60 :"PicamModel_Pixis1024BRExcelon",
	16 :"PicamModel_PixisXO1024F",
	14 :"PicamModel_PixisXO1024B",
	15 :"PicamModel_PixisXO1024BR",
	17 :"PicamModel_PixisXF1024F",
	18 :"PicamModel_PixisXF1024B",
	71 :"PicamModel_PixisXB1024BR",
	51 :"PicamModel_Pixis1300Series",
	52 :"PicamModel_Pixis1300F",
	75 :"PicamModel_Pixis1300F_2",
	53 :"PicamModel_Pixis1300B",
	73 :"PicamModel_Pixis1300BR",
	61 :"PicamModel_Pixis1300BExcelon",
	62 :"PicamModel_Pixis1300BRExcelon",
	65 :"PicamModel_PixisXO1300B",
	66 :"PicamModel_PixisXF1300B",
	72 :"PicamModel_PixisXB1300R",
	20 :"PicamModel_Pixis2048Series",
	21 :"PicamModel_Pixis2048F",
	22 :"PicamModel_Pixis2048B",
	67 :"PicamModel_Pixis2048BR",
	63 :"PicamModel_Pixis2048BExcelon",
	74 :"PicamModel_Pixis2048BRExcelon",
	23 :"PicamModel_PixisXO2048B",
	25 :"PicamModel_PixisXF2048F",
	24 :"PicamModel_PixisXF2048B",
	32 :"PicamModel_Pixis2KSeries",
	33 :"PicamModel_Pixis2KF",
	34 :"PicamModel_Pixis2KB",
	36 :"PicamModel_Pixis2KBUV",
	64 :"PicamModel_Pixis2KBExcelon",
	35 :"PicamModel_PixisXO2KB",
	100 :"PicamModel_QuadroSeries",
	101 :"PicamModel_Quadro4096",
	103 :"PicamModel_Quadro4096_2",
	102 :"PicamModel_Quadro4320",
	200 :"PicamModel_ProEMSeries",
	203 :"PicamModel_ProEM512Series",
	201 :"PicamModel_ProEM512B",
	205 :"PicamModel_ProEM512BK",
	204 :"PicamModel_ProEM512BExcelon",
	206 :"PicamModel_ProEM512BKExcelon",
	207 :"PicamModel_ProEM1024Series",
	202 :"PicamModel_ProEM1024B",
	208 :"PicamModel_ProEM1024BExcelon",
	209 :"PicamModel_ProEM1600Series",
	212 :"PicamModel_ProEM1600xx2B",
	210 :"PicamModel_ProEM1600xx2BExcelon",
	213 :"PicamModel_ProEM1600xx4B",
	211 :"PicamModel_ProEM1600xx4BExcelon",
	600 :"PicamModel_ProEMPlusSeries",
	603 :"PicamModel_ProEMPlus512Series",
	601 :"PicamModel_ProEMPlus512B",
	605 :"PicamModel_ProEMPlus512BK",
	604 :"PicamModel_ProEMPlus512BExcelon",
	606 :"PicamModel_ProEMPlus512BKExcelon",
	607 :"PicamModel_ProEMPlus1024Series",
	602 :"PicamModel_ProEMPlus1024B",
	608 :"PicamModel_ProEMPlus1024BExcelon",
	609 :"PicamModel_ProEMPlus1600Series",
	612 :"PicamModel_ProEMPlus1600xx2B",
	610 :"PicamModel_ProEMPlus1600xx2BExcelon",
	613 :"PicamModel_ProEMPlus1600xx4B",
	611 :"PicamModel_ProEMPlus1600xx4BExcelon",
	1200 :"PicamModel_ProEMHSSeries",
	1201 :"PicamModel_ProEMHS512Series",
	1202 :"PicamModel_ProEMHS512B",
	1207 :"PicamModel_ProEMHS512BK",
	1203 :"PicamModel_ProEMHS512BExcelon",
	1208 :"PicamModel_ProEMHS512BKExcelon",
	1216 :"PicamModel_ProEMHS512B_2",
	1217 :"PicamModel_ProEMHS512BExcelon_2",
	1204 :"PicamModel_ProEMHS1024Series",
	1205 :"PicamModel_ProEMHS1024B",
	1206 :"PicamModel_ProEMHS1024BExcelon",
	1212 :"PicamModel_ProEMHS1024B_2",
	1213 :"PicamModel_ProEMHS1024BExcelon_2",
	1214 :"PicamModel_ProEMHS1024B_3",
	1215 :"PicamModel_ProEMHS1024BExcelon_3",
	1209 :"PicamModel_ProEMHS1K10Series",
	1210 :"PicamModel_ProEMHS1KB10",
	1211 :"PicamModel_ProEMHS1KB10Excelon",
	300 :"PicamModel_PIMax3Series",
	301 :"PicamModel_PIMax31024I",
	302 :"PicamModel_PIMax31024x256",
	700 :"PicamModel_PIMax4Series",
	703 :"PicamModel_PIMax41024ISeries",
	701 :"PicamModel_PIMax41024I",
	704 :"PicamModel_PIMax41024IRF",
	710 :"PicamModel_PIMax41024FSeries",
	711 :"PicamModel_PIMax41024F",
	712 :"PicamModel_PIMax41024FRF",
	705 :"PicamModel_PIMax41024x256Series",
	702 :"PicamModel_PIMax41024x256",
	706 :"PicamModel_PIMax41024x256RF",
	716 :"PicamModel_PIMax42048Series",
	717 :"PicamModel_PIMax42048F",
	718 :"PicamModel_PIMax42048B",
	719 :"PicamModel_PIMax42048FRF",
	720 :"PicamModel_PIMax42048BRF",
	708 :"PicamModel_PIMax4512EMSeries",
	707 :"PicamModel_PIMax4512EM",
	709 :"PicamModel_PIMax4512BEM",
	713 :"PicamModel_PIMax41024EMSeries",
	715 :"PicamModel_PIMax41024EM",
	714 :"PicamModel_PIMax41024BEM",
	400 :"PicamModel_PylonSeries",
	418 :"PicamModel_Pylon100Series",
	404 :"PicamModel_Pylon100F",
	401 :"PicamModel_Pylon100B",
	407 :"PicamModel_Pylon100BR",
	425 :"PicamModel_Pylon100BExcelon",
	426 :"PicamModel_Pylon100BRExcelon",
	419 :"PicamModel_Pylon256Series",
	409 :"PicamModel_Pylon256F",
	410 :"PicamModel_Pylon256B",
	411 :"PicamModel_Pylon256E",
	412 :"PicamModel_Pylon256BR",
	420 :"PicamModel_Pylon400Series",
	405 :"PicamModel_Pylon400F",
	402 :"PicamModel_Pylon400B",
	408 :"PicamModel_Pylon400BR",
	427 :"PicamModel_Pylon400BExcelon",
	428 :"PicamModel_Pylon400BRExcelon",
	421 :"PicamModel_Pylon1024Series",
	417 :"PicamModel_Pylon1024B",
	429 :"PicamModel_Pylon1024BExcelon",
	422 :"PicamModel_Pylon1300Series",
	406 :"PicamModel_Pylon1300F",
	403 :"PicamModel_Pylon1300B",
	438 :"PicamModel_Pylon1300R",
	432 :"PicamModel_Pylon1300BR",
	430 :"PicamModel_Pylon1300BExcelon",
	433 :"PicamModel_Pylon1300BRExcelon",
	423 :"PicamModel_Pylon2048Series",
	415 :"PicamModel_Pylon2048F",
	434 :"PicamModel_Pylon2048B",
	416 :"PicamModel_Pylon2048BR",
	435 :"PicamModel_Pylon2048BExcelon",
	436 :"PicamModel_Pylon2048BRExcelon",
	424 :"PicamModel_Pylon2KSeries",
	413 :"PicamModel_Pylon2KF",
	414 :"PicamModel_Pylon2KB",
	437 :"PicamModel_Pylon2KBUV",
	431 :"PicamModel_Pylon2KBExcelon",
	900 :"PicamModel_PylonirSeries",
	901 :"PicamModel_Pylonir1024Series",
	902 :"PicamModel_Pylonir102422",
	903 :"PicamModel_Pylonir102417",
	500 :"PicamModel_PionirSeries",
	501 :"PicamModel_Pionir640",
	800 :"PicamModel_NirvanaSeries",
	801 :"PicamModel_Nirvana640",
	1300 :"PicamModel_NirvanaSTSeries",
	1301 :"PicamModel_NirvanaST640",
	1100 :"PicamModel_NirvanaLNSeries",
	1101 :"PicamModel_NirvanaLN640",
	1800 :"PicamModel_SophiaSeries",
	1801 :"PicamModel_Sophia2048Series",
	1802 :"PicamModel_Sophia2048B",
	1803 :"PicamModel_Sophia2048BExcelon",
	1804 :"PicamModel_SophiaXO2048B",
	1805 :"PicamModel_SophiaXF2048B",
	1806 :"PicamModel_SophiaXB2048B",
	1807 :"PicamModel_Sophia2048135Series",
	1808 :"PicamModel_Sophia2048135",
	1809 :"PicamModel_Sophia2048B135",
	1810 :"PicamModel_Sophia2048BR135",
	1811 :"PicamModel_Sophia2048B135Excelon",
	1812 :"PicamModel_Sophia2048BR135Excelon",
	1813 :"PicamModel_SophiaXO2048B135",
	1814 :"PicamModel_SophiaXO2048BR135",
	1500 :"PicamModel_BlazeSeries",
	1507 :"PicamModel_Blaze100Series",
	1501 :"PicamModel_Blaze100B",
	1505 :"PicamModel_Blaze100BR",
	1503 :"PicamModel_Blaze100HR",
	1509 :"PicamModel_Blaze100BRLD",
	1511 :"PicamModel_Blaze100BExcelon",
	1513 :"PicamModel_Blaze100BRExcelon",
	1515 :"PicamModel_Blaze100HRExcelon",
	1517 :"PicamModel_Blaze100BRLDExcelon",
	1508 :"PicamModel_Blaze400Series",
	1502 :"PicamModel_Blaze400B",
	1506 :"PicamModel_Blaze400BR",
	1504 :"PicamModel_Blaze400HR",
	1510 :"PicamModel_Blaze400BRLD",
	1512 :"PicamModel_Blaze400BExcelon",
	1514 :"PicamModel_Blaze400BRExcelon",
	1516 :"PicamModel_Blaze400HRExcelon",
	1518 :"PicamModel_Blaze400BRLDExcelon",
	1600 :"PicamModel_FergieSeries",
	1601 :"PicamModel_Fergie256Series",
	1602 :"PicamModel_Fergie256B",
	1607 :"PicamModel_Fergie256BR",
	1603 :"PicamModel_Fergie256BExcelon",
	1608 :"PicamModel_Fergie256BRExcelon",
	1604 :"PicamModel_Fergie256FTSeries",
	1609 :"PicamModel_Fergie256FFT",
	1605 :"PicamModel_Fergie256BFT",
	1610 :"PicamModel_Fergie256BRFT",
	1606 :"PicamModel_Fergie256BFTExcelon",
	1611 :"PicamModel_Fergie256BRFTExcelon",
	1700 :"PicamModel_FergieAccessorySeries",
	1701 :"PicamModel_FergieLampSeries",
	1702 :"PicamModel_FergieAEL",
	1703 :"PicamModel_FergieQTH",
	1704 :"PicamModel_FergieLaserSeries",
	1705 :"PicamModel_FergieLaser785",
	1900 :"PicamModel_KuroSeries",
	1901 :"PicamModel_Kuro1200B",
	1902 :"PicamModel_Kuro1608B",
	1903 :"PicamModel_Kuro2048B"
}

PicamComputerInterface = {
	1 :"PicamComputerInterface_Usb2",
	2 :"PicamComputerInterface_1394A",
	3 :"PicamComputerInterface_GigabitEthernet",
	4 :"PicamComputerInterface_Usb3",
}

PicamStringSize = {
	64 :"PicamStringSize_SensorName",
	64 :"PicamStringSize_SerialNumber",
	64 :"PicamStringSize_FirmwareName",
	256 :"PicamStringSize_FirmwareDetail",
}

PicamValueType = {
	1 :"PicamValueType_Integer",
	3 :"PicamValueType_Boolean",
	4 :"PicamValueType_Enumeration",
	6 :"PicamValueType_LargeInteger",
	2 :"PicamValueType_FloatingPoint",
	5 :"PicamValueType_Rois",
	7 :"PicamValueType_Pulse",
	8 :"PicamValueType_Modulations",
}

PicamConstraintType = {
	1 :"PicamConstraintType_None",
	2 :"PicamConstraintType_Range",
	3 :"PicamConstraintType_Collection",
	4 :"PicamConstraintType_Rois",
	5 :"PicamConstraintType_Pulse",
	6 :"PicamConstraintType_Modulations",
}



PicamActiveShutter = {
	1 :"PicamActiveShutter_None",
	2 :"PicamActiveShutter_Internal",
	3 :"PicamActiveShutter_External"
}

PicamAdcAnalogGain ={
	1 :"PicamAdcAnalogGain_Low",
	2 :"PicamAdcAnalogGain_Medium",
	3 :"PicamAdcAnalogGain_High"
}

PicamAdcQuality = {
	1 :"PicamAdcQuality_LowNoise",
	2 :"PicamAdcQuality_HighCapacity",
	4 :"PicamAdcQuality_HighSpeed",
	3 :"PicamAdcQuality_ElectronMultiplied"
}

PicamCcdCharacteristicsMask = {
	0x000 :"PicamCcdCharacteristicsMask_None",
	0x001 :"PicamCcdCharacteristicsMask_BackIlluminated",
	0x002 :"PicamCcdCharacteristicsMask_DeepDepleted",
	0x004 :"PicamCcdCharacteristicsMask_OpenElectrode",
	0x008 :"PicamCcdCharacteristicsMask_UVEnhanced",
	0x010 :"PicamCcdCharacteristicsMask_ExcelonEnabled",
	0x020 :"PicamCcdCharacteristicsMask_SecondaryMask",
	0x040 :"PicamCcdCharacteristicsMask_Multiport",
	0x080 :"PicamCcdCharacteristicsMask_AdvancedInvertedMode",
	0x100 :"PicamCcdCharacteristicsMask_HighResistivity"
}

PicamCenterWavelengthStatus = {
	1 :"PicamCenterWavelengthStatus_Moving",
	2 :"PicamCenterWavelengthStatus_Stationary",
	3 :"PicamCenterWavelengthStatus_Faulted"
}

PicamCoolingFanStatus = {
	1 :"PicamCoolingFanStatus_Off",
	2 :"PicamCoolingFanStatus_On",
	3 :"PicamCoolingFanStatus_ForcedOn"
}

PicamEMIccdGainControlMode = {
	1 :"PicamEMIccdGainControlMode_Optimal",
	2 :"PicamEMIccdGainControlMode_Manual"
}

PicamGateTrackingMask = {
	0x0 :"PicamGateTrackingMask_None",
	0x1 :"PicamGateTrackingMask_Delay",
	0x2 :"PicamGateTrackingMask_Width"
}

PicamGatingMode = {
	4 :"PicamGatingMode_Disabled",
	1 :"PicamGatingMode_Repetitive",
	2 :"PicamGatingMode_Sequential",
	3 :"PicamGatingMode_Custom"
}

PicamGatingSpeed = {
	1 :"PicamGatingSpeed_Fast",
	2 :"PicamGatingSpeed_Slow"
}

PicamGratingCoating = {
	1 :"PicamGratingCoating_Al",
	4 :"PicamGratingCoating_AlMgF2",
	2 :"PicamGratingCoating_Ag",
	3 :"PicamGratingCoating_Au"
}

PicamGratingType = {
	1 :"PicamGratingType_Ruled",
	2 :"PicamGratingType_HolographicVisible",
	3 :"PicamGratingType_HolographicNir",
	4 :"PicamGratingType_HolographicUV",
	5 :"PicamGratingType_Mirror"
}

PicamIntensifierOptionsMask = {
	0x0 :"PicamIntensifierOptionsMask_None",
	0x1 :"PicamIntensifierOptionsMask_McpGating",
	0x2 :"PicamIntensifierOptionsMask_SubNanosecondGating",
	0x4 :"PicamIntensifierOptionsMask_Modulation",
}

PicamIntensifierStatus = {
	1 :"PicamIntensifierStatus_PoweredOff",
	2 :"PicamIntensifierStatus_PoweredOn",
}

PicamLaserOutputMode = {
	1 :"PicamLaserOutputMode_Disabled",
	2 :"PicamLaserOutputMode_ContinuousWave",
	3 :"PicamLaserOutputMode_Pulsed",
}
PicamLaserStatus = {
	1 :"PicamLaserStatus_Disarmed",
	2 :"PicamLaserStatus_Unarmed",
	3 :"PicamLaserStatus_Arming",
	4 :"PicamLaserStatus_Armed",
}
PicamLightSource = {
	1 :"PicamLightSource_Disabled",
	2 :"PicamLightSource_Hg",
	3 :"PicamLightSource_NeAr",
	4 :"PicamLightSource_Qth",
}

LightSourceStatus = {
	1 :"PicamLightSourceStatus_Unstable",
	2 :"PicamLightSourceStatus_Stable",
}

PicamModulationTrackingMask = {
	0x0 :"PicamModulationTrackingMask_None",
	0x1 :"PicamModulationTrackingMask_Duration",
	0x2 :"PicamModulationTrackingMask_Frequency",
	0x4 :"PicamModulationTrackingMask_Phase",
	0x8 :"PicamModulationTrackingMask_OutputSignalFrequency",
}

PicamOrientationMask = {
	0x0 :"PicamOrientationMask_Normal",
	0x1 :"PicamOrientationMask_FlippedHorizontally",
	0x2 :"PicamOrientationMask_FlippedVertically",
}

PicamOutputSignal = {
	6 :"PicamOutputSignal_Acquiring",
	5 :"PicamOutputSignal_AlwaysHigh",
	4 :"PicamOutputSignal_AlwaysLow",
	14 :"PicamOutputSignal_AuxOutput",
	3 :"PicamOutputSignal_Busy",
	9 :"PicamOutputSignal_EffectivelyExposing",
	15 :"PicamOutputSignal_EffectivelyExposingAlternation",
	8 :"PicamOutputSignal_Exposing",
	13 :"PicamOutputSignal_Gate",
	12 :"PicamOutputSignal_InternalTriggerT0",
	1 :"PicamOutputSignal_NotReadingOut",
	10 :"PicamOutputSignal_ReadingOut",
	7 :"PicamOutputSignal_ShiftingUnderMask",
	2 :"PicamOutputSignal_ShutterOpen",
	11 :"PicamOutputSignal_WaitingForTrigger",
}

PicamPhosphorType = {
	1 :"PicamPhosphorType_P43",
	2 :"PicamPhosphorType_P46",
}
PicamPhotocathodeSensitivity = {
	1 :"PicamPhotocathodeSensitivity_RedBlue",
	7 :"PicamPhotocathodeSensitivity_SuperRed",
	2 :"PicamPhotocathodeSensitivity_SuperBlue",
	3 :"PicamPhotocathodeSensitivity_UV",
	10 :"PicamPhotocathodeSensitivity_SolarBlind",
	4 :"PicamPhotocathodeSensitivity_Unigen2Filmless",
	9 :"PicamPhotocathodeSensitivity_InGaAsFilmless",
	5 :"PicamPhotocathodeSensitivity_HighQEFilmless",
	8 :"PicamPhotocathodeSensitivity_HighRedFilmless",
	6 :"PicamPhotocathodeSensitivity_HighBlueFilmless",
}
PicamPhotonDetectionMode = {
	1 :"PicamPhotonDetectionMode_Disabled",
	2 :"PicamPhotonDetectionMode_Thresholding",
	3 :"PicamPhotonDetectionMode_Clipping",
}
PicamPixelFormat = {
	1 :"PicamPixelFormat_Monochrome16Bit",
	2 :"PicamPixelFormat_Monochrome32Bit",
}
PicamReadoutControlMode = {
	1 :"PicamReadoutControlMode_FullFrame",
	2 :"PicamReadoutControlMode_FrameTransfer",
	5 :"PicamReadoutControlMode_Interline",
	8 :"PicamReadoutControlMode_RollingShutter",
	3 :"PicamReadoutControlMode_Kinetics",
	4 :"PicamReadoutControlMode_SpectraKinetics",
	6 :"PicamReadoutControlMode_Dif",
	7 :"PicamReadoutControlMode_SeNsR",
}
PicamSensorTemperatureStatus = {
	1 :"PicamSensorTemperatureStatus_Unlocked",
	2 :"PicamSensorTemperatureStatus_Locked",
	3 :"PicamSensorTemperatureStatus_Faulted",
}
PicamSensorType = {
	1 :"PicamSensorType_Ccd",
	2 :"PicamSensorType_InGaAs",
	3 :"PicamSensorType_Cmos",
}
PicamShutterStatus = {
	1 :"PicamShutterStatus_NotConnected",
	2 :"PicamShutterStatus_Connected",
	3 :"PicamShutterStatus_Overheated",
}
PicamShutterTimingMode = {
	1 :"PicamShutterTimingMode_Normal",
	2 :"PicamShutterTimingMode_AlwaysClosed",
	3 :"PicamShutterTimingMode_AlwaysOpen",
	4 :"PicamShutterTimingMode_OpenBeforeTrigger",
}
PicamShutterType = {
	1 :"PicamShutterType_None",
	2 :"PicamShutterType_VincentCS25",
	3 :"PicamShutterType_VincentCS45",
	9 :"PicamShutterType_VincentCS90",
	8 :"PicamShutterType_VincentDSS10",
	4 :"PicamShutterType_VincentVS25",
	5 :"PicamShutterType_VincentVS35",
	6 :"PicamShutterType_ProntorMagnetic0",
	7 :"PicamShutterType_ProntorMagneticE40",
}
PicamTimeStampsMask = {
	0x0 :"PicamTimeStampsMask_None",
	0x1 :"PicamTimeStampsMask_ExposureStarted",
	0x2 :"PicamTimeStampsMask_ExposureEnded",
}
PicamTriggerCoupling = {
	1 :"PicamTriggerCoupling_AC",
	2 :"PicamTriggerCoupling_DC",
}
PicamTriggerDetermination = {
	1 :"PicamTriggerDetermination_PositivePolarity",
	2 :"PicamTriggerDetermination_NegativePolarity",
	3 :"PicamTriggerDetermination_RisingEdge",
	4 :"PicamTriggerDetermination_FallingEdge",
	5 :"PicamTriggerDetermination_AlternatingEdgeRising",
	6 :"PicamTriggerDetermination_AlternatingEdgeFalling",
}

PicamTriggerResponse = {
	1 :"PicamTriggerResponse_NoResponse",
	5 :"PicamTriggerResponse_StartOnSingleTrigger",
	2 :"PicamTriggerResponse_ReadoutPerTrigger",
	3 :"PicamTriggerResponse_ShiftPerTrigger",
	6 :"PicamTriggerResponse_GatePerTrigger",
	4 :"PicamTriggerResponse_ExposeDuringTriggerPulse",
}

PicamTriggerSource = {
	3 :"PicamTriggerSource_None",
	2 :"PicamTriggerSource_Internal",
	1 :"PicamTriggerSource_External",
}

PicamTriggerStatus = {
	1 :"PicamTriggerStatus_NotConnected",
	2 :"PicamTriggerStatus_Connected",
}

PicamTriggerTermination = {
	1 :"PicamTriggerTermination_FiftyOhms",
	2 :"PicamTriggerTermination_HighImpedance",
}

PicamVacuumStatus = {
	1 :"PicamVacuumStatus_Sufficient",
	2 :"PicamVacuumStatus_Low",
}
typedefenumPicamValueAccess = {
	1 :"PicamValueAccess_ReadOnly",
	3 :"PicamValueAccess_ReadWriteTrivial",
	2 :"PicamValueAccess_ReadWrite",
}

PicamConstraintScope ={
	1 :"PicamConstraintScope_Independent",
	2 :"PicamConstraintScope_Dependent",
}
PicamConstraintSeverity = {
	1 :"PicamConstraintSeverity_Error",
	2 :"PicamConstraintSeverity_Warning",
}

PicamConstraintCategory = {
	1 :"PicamConstraintCategory_Capable",
	2 :"PicamConstraintCategory_Required",
	3 :"PicamConstraintCategory_Recommended",
}

PicamRoisConstraintRulesMask ={
	0x00 :"PicamRoisConstraintRulesMask_None",
	0x01 :"PicamRoisConstraintRulesMask_XBinningAlignment",
	0x02 :"PicamRoisConstraintRulesMask_YBinningAlignment",
	0x04 :"PicamRoisConstraintRulesMask_HorizontalSymmetry",
	0x08 :"PicamRoisConstraintRulesMask_VerticalSymmetry",
	0x10 :"PicamRoisConstraintRulesMask_SymmetryBoundsBinning",
}
PicamAcquisitionErrorsMask = {
	0x00 :"PicamAcquisitionErrorsMask_None",
	0x10 :"PicamAcquisitionErrorsMask_CameraFaulted",
	0x02 :"PicamAcquisitionErrorsMask_ConnectionLost",
	0x08 :"PicamAcquisitionErrorsMask_ShutterOverheated",
	0x01 :"PicamAcquisitionErrorsMask_DataLost",
	0x04 :"PicamAcquisitionErrorsMask_DataNotArriving",
}

if __name__ == "__main__":

	#Perform basic tests
	expected_value = 16908303 #ExposureTime
	(value_type, constraint_type, n) = PicamParameter["PicamParameter_SensorTemperatureReading"]
	print(value_type, constraint_type,n) 
	computed_value = PI_V(value_type,constraint_type,n)
	assert(expected_value==computed_value)
	#Parameter dictionary
	# for k in PicamParameter.keys():
	# 	(value_type, constraint_type, n) = PicamParameter[k]
	# 	v = PI_V(value_type,constraint_type,n)
	# 	print k,":",v