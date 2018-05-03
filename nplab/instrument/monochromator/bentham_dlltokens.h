//-----------------------------------------------------------------------------
// Bentham Instruments Spectroradiometer Control DLL
//Attribute token definition file
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// Monochromator attributes
//-----------------------------------------------------------------------------
#define MonochromatorScanDirection 10
#define MonochromatorCurrentWL 11
#define MonochromatorCurrentDialReading 12
#define MonochromatorParkDialReading 13
#define MonochromatorCurrentGrating 14
#define MonochromatorPark 15
#define MonochromatorSelfPark 16
#define MonochromatorModeSwitchNum 17
#define MonochromatorModeSwitchState 18
#define MonochromatorCanModeSwitch 19

#define Gratingd 20
#define GratingZ 21
#define GratingA 22
#define GratingWLMin 23
#define GratingWLMax 24
#define GratingX2 25
#define GratingX1 26
#define GratingX 27

#define ChangerZ 50

//-----------------------------------------------------------------------------
// Filter wheel attributes
//-----------------------------------------------------------------------------
#define FWheelFilter 100
#define FWheelPositions 101
#define FWheelCurrentPosition 102

//-----------------------------------------------------------------------------
// TLS attributes
//-----------------------------------------------------------------------------
#define TLSCurrentPosition 150
#define TLSWL 151
#define TLSPOS 152
#define TLSSelectWavelength 153
#define TLSPositionsCommand 154

//-----------------------------------------------------------------------------
// Switch-over box attributes
//-----------------------------------------------------------------------------
#define SOBInitialState 200
#define SOBState 202

//-----------------------------------------------------------------------------
// SAM attributes
//-----------------------------------------------------------------------------
#define SAMInitialState 300
#define SAMSwitchWL 301
#define SAMState 302
#define SAMCurrentState 303

//-----------------------------------------------------------------------------
// Stepper SAM attributes
//-----------------------------------------------------------------------------
#define SSEnergisedSteps 320
#define SSRelaxedSteps 321
#define SSMaxSteps 322
#define SSSpeed 323
#define SSMoveCurrent 324
#define SSIdleCurrent 325

//-----------------------------------------------------------------------------
// 262
//-----------------------------------------------------------------------------
#define biRelay 350
#define biCurrentRelay 351

//-----------------------------------------------------------------------------
// MVSS attributes
//-----------------------------------------------------------------------------
#define MVSSSwitchWL 401
#define MVSSWidth 402
#define MVSSCurrentWidth 403
#define MVSSSetWidth 404
#define MVSSConstantBandwidth 405
#define MVSSConstantwidth 406
#define MVSSSlitMode 407
#define MVSSPosition 408

//-----------------------------------------------------------------------------
// ADC attributes
//-----------------------------------------------------------------------------
#define ADCSamplesPerReading 500
#define ADCAdaptiveIntegration 501
#define ADCSamplePeriod 502
#define ADCVolts 504

//-----------------------------------------------------------------------------
// ADC CHOPPER attributes
//-----------------------------------------------------------------------------
#define ADCChoppedAverages 503

//-----------------------------------------------------------------------------
// General amplifier attributes
//-----------------------------------------------------------------------------
#define AmpGain 600
#define AmpChannel 601
#define AmpMinRange 602
#define AmpMaxRange 603
#define AmpStartRange 604
#define AmpUseSetup 605
#define AmpCurrentRange 606
#define AmpCurrentChannel 607
#define AmpOverload 608
#define AmpOverrideWl 609

//-----------------------------------------------------------------------------
// 225 attributes
//-----------------------------------------------------------------------------
#define A225TargetRange 700
#define A225PhaseVariable 701
#define A225PhaseQuadrant 702
#define A225TimeConstant 703
#define A225fMode 704

//-----------------------------------------------------------------------------
// Camera attributes
//-----------------------------------------------------------------------------
#define CameraIntegrationTime 800
#define CameraMinWl 801
#define CameraMaxWl 802
#define CameraNumPixelsW 803
#define CameraWidth 804
#define CameraDataSize_nm 805
#define CameraSAMState 806
#define CameraAutoRange 807
#define CameraMVSSWidth 808
#define CameraAverages 809
#define CameraMinITime 810
#define CameraMaxITime 811
#define CameraUnitMaxITime 812
#define CameraZCITime 813
#define CameraZCAverages 814
#define CameraDataLToR 815

//-----------------------------------------------------------------------------
// Motorised Stage attributes
//-----------------------------------------------------------------------------
#define MotorPosition 900

//-----------------------------------------------------------------------------
// Miscellaneous attributes
//-----------------------------------------------------------------------------
#define biSettleDelay 1000
#define biMin 1001
#define biMax 1002
#define biParkPos 1003
#define biInput 1004
#define biCurrentInput 1005
#define biMoveWithWavelength 1006
#define biHasSetupWindow 1007
#define biHasAdvancedWindow 1008
#define biDescriptor 1009
#define biParkOffset 1010
#define biProductName 1011

//-----------------------------------------------------------------------------
// System attributes
//-----------------------------------------------------------------------------
#define SysStopCount 9000
#define SysDarkIIntegrationTime 9001
#define Sys225_277Input 9002

//-----------------------------------------------------------------------------
// Bentham Hardware Types
//-----------------------------------------------------------------------------
#define BenInterface 10000
#define BenSAM 10001
#define BenSlit 10002
#define BenFilterWheel 10003
#define BenADC 10004
#define BenPREAMP 10005
#define BenACAMP 10006
#define BenDCAMP 10007
#define BenPOSTAMP 10012
#define BenRelayUnit 10008
#define BenMono 10009
#define BenAnonDevice 10010
#define BenCamera 10020
#define BenDiodeArray 10021
#define BenORM 10022

#define BenUnknown 10011
