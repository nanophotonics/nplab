/**********************************************************************
* Copyright (c) 2006-2013 SmarAct GmbH
*
* File name: MCSControl.h
* Author   : Marc Schiffner
* Version  : 2.0.1
*
* This is the software interface to the Modular Control System.
* Please refer to the Programmer's Guide for a detailed documentation.
*
* THIS  SOFTWARE, DOCUMENTS, FILES AND INFORMATION ARE PROVIDED 'AS IS'
* WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING,
* BUT  NOT  LIMITED  TO,  THE  IMPLIED  WARRANTIES  OF MERCHANTABILITY,
* FITNESS FOR A PURPOSE, OR THE WARRANTY OF NON-INFRINGEMENT.
* THE  ENTIRE  RISK  ARISING OUT OF USE OR PERFORMANCE OF THIS SOFTWARE
* REMAINS WITH YOU.
* IN  NO  EVENT  SHALL  THE  SMARACT  GMBH  BE  LIABLE  FOR ANY DIRECT,
* INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL OR OTHER DAMAGES ARISING
* OUT OF THE USE OR INABILITY TO USE THIS SOFTWARE.
**********************************************************************/

#ifndef MCSCONTROL_H
#define MCSCONTROL_H

#define SA_MCSCONTROL_VERSION_MAJOR                 2
#define SA_MCSCONTROL_VERSION_MINOR                 0
#define SA_MCSCONTROL_VERSION_UPDATE                1

#if defined(_WIN32)
#  define SA_PLATFORM_WINDOWS
#elif defined(__linux__)
#  define SA_PLATFORM_LINUX
#else
#  error "unsupported platform"
#endif


#ifdef SA_PLATFORM_WINDOWS
#  ifdef MCSCONTROL_EXPORTS
#    define MCSCONTROL_API __declspec(dllexport)
#  else
#    define MCSCONTROL_API __declspec(dllimport)
#  endif
#  define MCSCONTROL_CC __cdecl
#else
#  define MCSCONTROL_API __attribute__ ((visibility ("default")))
#  define MCSCONTROL_CC
#endif


typedef unsigned int SA_STATUS;
typedef unsigned int SA_INDEX;
typedef unsigned int SA_PACKET_TYPE;

// defines a data packet for the asynchronous mode
typedef struct SA_packet {
    SA_PACKET_TYPE packetType;                      // type of packet (see below)
    SA_INDEX channelIndex;                          // source channel
    unsigned int data1;                             // data field
    signed int data2;                               // data field
    signed int data3;                               // data field
    unsigned int data4;                             // data field
} SA_PACKET;

// function status return values
#define SA_OK                                       0
#define SA_INITIALIZATION_ERROR                     1
#define SA_NOT_INITIALIZED_ERROR                    2
#define SA_NO_SYSTEMS_FOUND_ERROR                   3
#define SA_TOO_MANY_SYSTEMS_ERROR                   4
#define SA_INVALID_SYSTEM_INDEX_ERROR               5
#define SA_INVALID_CHANNEL_INDEX_ERROR              6
#define SA_TRANSMIT_ERROR                           7
#define SA_WRITE_ERROR                              8
#define SA_INVALID_PARAMETER_ERROR                  9
#define SA_READ_ERROR                               10
#define SA_INTERNAL_ERROR                           12
#define SA_WRONG_MODE_ERROR                         13
#define SA_PROTOCOL_ERROR                           14
#define SA_TIMEOUT_ERROR                            15
#define SA_ID_LIST_TOO_SMALL_ERROR                  17
#define SA_SYSTEM_ALREADY_ADDED_ERROR               18
#define SA_WRONG_CHANNEL_TYPE_ERROR                 19
#define SA_CANCELED_ERROR                           20
#define SA_INVALID_SYSTEM_LOCATOR_ERROR             21
#define SA_INPUT_BUFFER_OVERFLOW_ERROR              22
#define SA_QUERYBUFFER_SIZE_ERROR                   23
#define SA_NO_SENSOR_PRESENT_ERROR                  129
#define SA_AMPLITUDE_TOO_LOW_ERROR                  130
#define SA_AMPLITUDE_TOO_HIGH_ERROR                 131
#define SA_FREQUENCY_TOO_LOW_ERROR                  132
#define SA_FREQUENCY_TOO_HIGH_ERROR                 133
#define SA_SCAN_TARGET_TOO_HIGH_ERROR               135
#define SA_SCAN_SPEED_TOO_LOW_ERROR                 136
#define SA_SCAN_SPEED_TOO_HIGH_ERROR                137
#define SA_SENSOR_DISABLED_ERROR                    140
#define SA_COMMAND_OVERRIDDEN_ERROR                 141
#define SA_END_STOP_REACHED_ERROR                   142
#define SA_WRONG_SENSOR_TYPE_ERROR                  143
#define SA_COULD_NOT_FIND_REF_ERROR                 144
#define SA_WRONG_END_EFFECTOR_TYPE_ERROR            145
#define SA_MOVEMENT_LOCKED_ERROR                    146
#define SA_RANGE_LIMIT_REACHED_ERROR                147
#define SA_PHYSICAL_POSITION_UNKNOWN_ERROR          148
#define SA_OUTPUT_BUFFER_OVERFLOW_ERROR             149
#define SA_COMMAND_NOT_PROCESSABLE_ERROR            150
#define SA_WAITING_FOR_TRIGGER_ERROR                151
#define SA_COMMAND_NOT_TRIGGERABLE_ERROR            152
#define SA_COMMAND_QUEUE_FULL_ERROR                 153
#define SA_INVALID_COMPONENT_ERROR                  154
#define SA_INVALID_SUB_COMPONENT_ERROR              155
#define SA_INVALID_PROPERTY_ERROR                   156
#define SA_PERMISSION_DENIED_ERROR                  157
#define SA_UNKNOWN_COMMAND_ERROR                    240
#define SA_OTHER_ERROR                              255

// general definitions
#define SA_UNDEFINED                                0
#define SA_FALSE                                    0
#define SA_TRUE                                     1
#define SA_DISABLED                                 0
#define SA_ENABLED                                  1
#define SA_FALLING_EDGE                             0
#define SA_RISING_EDGE                              1
#define SA_FORWARD                                  0
#define SA_BACKWARD                                 1

// component selectors
#define SA_GENERAL                                  1
#define SA_DIGITAL_IN                               2
#define SA_ANALOG_IN                                3
#define SA_COUNTER                                  4
#define SA_CAPTURE_BUFFER                           5
#define SA_COMMAND_QUEUE                            6
#define SA_SOFTWARE_TRIGGER                         7
#define SA_SENSOR                                   8
#define SA_MONITOR                                  9

// general component sub selectors
#define SA_EMERGENCY_STOP                           1
#define SA_LOW_VIBRATION                            2

#define SA_BROADCAST_STOP                           4
#define SA_POSITION_CONTROL                         5

#define SA_POWER_SUPPLY                             11

#define SA_SCALE                                    22

// component properties
#define SA_OPERATION_MODE                           1
#define SA_ACTIVE_EDGE                              2
#define SA_TRIGGER_SOURCE                           3
#define SA_SIZE                                     4
#define SA_VALUE                                    5
#define SA_CAPACITY                                 6
#define SA_DIRECTION                                7
#define SA_SETPOINT                                 8
#define SA_P_GAIN                                   9
#define SA_P_RIGHT_SHIFT                            10
#define SA_I_GAIN                                   11
#define SA_I_RIGHT_SHIFT                            12
#define SA_D_GAIN                                   13
#define SA_D_RIGHT_SHIFT                            14
#define SA_ANTI_WINDUP                              15
#define SA_PID_LIMIT                                16
#define SA_FORCED_SLIP                              17

#define SA_THRESHOLD                                38
#define SA_DEFAULT_OPERATION_MODE                   45

#define SA_OFFSET                                   47

// operation mode property values for SA_EMERGENCY_STOP sub selector
#define SA_ESM_NORMAL                               0
#define SA_ESM_RESTRICTED                           1
#define SA_ESM_DISABLED                             2
#define SA_ESM_AUTO_RELEASE                         3

// configuration flags for SA_InitDevices
#define SA_SYNCHRONOUS_COMMUNICATION                0
#define SA_ASYNCHRONOUS_COMMUNICATION               1
#define SA_HARDWARE_RESET                           2

// return values from SA_GetInitState
#define SA_INIT_STATE_NONE                          0
#define SA_INIT_STATE_SYNC                          1
#define SA_INIT_STATE_ASYNC                         2

// return values for SA_GetChannelType
#define SA_POSITIONER_CHANNEL_TYPE                  0
#define SA_END_EFFECTOR_CHANNEL_TYPE                1

// Hand Control Module modes for SA_SetHCMEnabled
#define SA_HCM_DISABLED                             0
#define SA_HCM_ENABLED                              1
#define SA_HCM_CONTROLS_DISABLED                    2

// configuration values for SA_SetBufferedOutput_A
#define SA_UNBUFFERED_OUTPUT                        0
#define SA_BUFFERED_OUTPUT                          1

// configuration values for SA_SetStepWhileScan_X
#define SA_NO_STEP_WHILE_SCAN                       0
#define SA_STEP_WHILE_SCAN                          1

// configuration values for SA_SetAccumulateRelativePositions_X
#define SA_NO_ACCUMULATE_RELATIVE_POSITIONS         0
#define SA_ACCUMULATE_RELATIVE_POSITIONS            1

// configuration values for SA_SetSensorEnabled_X
#define SA_SENSOR_DISABLED                          0
#define SA_SENSOR_ENABLED                           1
#define SA_SENSOR_POWERSAVE                         2

// movement directions for SA_FindReferenceMark_X
#define SA_FORWARD_DIRECTION                        0
#define SA_BACKWARD_DIRECTION                       1
#define SA_FORWARD_BACKWARD_DIRECTION               2
#define SA_BACKWARD_FORWARD_DIRECTION               3
#define SA_FORWARD_DIRECTION_ABORT_ON_ENDSTOP       4
#define SA_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP      5
#define SA_FORWARD_BACKWARD_DIRECTION_ABORT_ON_ENDSTOP 6
#define SA_BACKWARD_FORWARD_DIRECTION_ABORT_ON_ENDSTOP 7

// configuration values for SA_FindReferenceMark_X
#define SA_NO_AUTO_ZERO                             0
#define SA_AUTO_ZERO                                1

// return values for SA_GetPhyscialPositionKnown_X
#define SA_PHYSICAL_POSITION_UNKNOWN                0
#define SA_PHYSICAL_POSITION_KNOWN                  1

// infinite timeout for functions that wait
#define SA_TIMEOUT_INFINITE                         0xFFFFFFFF

// sensor types for SA_SetSensorType_X and SA_GetSensorType_X
#define SA_NO_SENSOR_TYPE                           0
#define SA_S_SENSOR_TYPE                            1
#define SA_SR_SENSOR_TYPE                           2
#define SA_ML_SENSOR_TYPE                           3
#define SA_MR_SENSOR_TYPE                           4
#define SA_SP_SENSOR_TYPE                           5
#define SA_SC_SENSOR_TYPE                           6
#define SA_M25_SENSOR_TYPE                          7
#define SA_SR20_SENSOR_TYPE                         8
#define SA_M_SENSOR_TYPE                            9
#define SA_GC_SENSOR_TYPE                           10
#define SA_GD_SENSOR_TYPE                           11
#define SA_GE_SENSOR_TYPE                           12
#define SA_RA_SENSOR_TYPE                           13
#define SA_GF_SENSOR_TYPE                           14
#define SA_RB_SENSOR_TYPE                           15
#define SA_G605S_SENSOR_TYPE                        16
#define SA_G775S_SENSOR_TYPE                        17
#define SA_SC500_SENSOR_TYPE                        18
#define SA_G955S_SENSOR_TYPE                        19
#define SA_SR77_SENSOR_TYPE                         20
#define SA_SD_SENSOR_TYPE                           21
#define SA_R20ME_SENSOR_TYPE                        22
#define SA_SR2_SENSOR_TYPE                          23
#define SA_SCD_SENSOR_TYPE                          24
#define SA_SRC_SENSOR_TYPE                          25
#define SA_SR36M_SENSOR_TYPE                        26
#define SA_SR36ME_SENSOR_TYPE                       27
#define SA_SR50M_SENSOR_TYPE                        28
#define SA_SR50ME_SENSOR_TYPE                       29
#define SA_G1045S_SENSOR_TYPE                       30
#define SA_G1395S_SENSOR_TYPE                       31
#define SA_MD_SENSOR_TYPE                           32

// end effector types for SA_SetEndEffectorType_X and SA_GetEndEffectorType_X
#define SA_ANALOG_SENSOR_END_EFFECTOR_TYPE          0
#define SA_GRIPPER_END_EFFECTOR_TYPE                1
#define SA_FORCE_SENSOR_END_EFFECTOR_TYPE           2
#define SA_FORCE_GRIPPER_END_EFFECTOR_TYPE          3

// packet types for asynchronous mode
#define SA_NO_PACKET_TYPE                           0
#define SA_ERROR_PACKET_TYPE                        1
#define SA_POSITION_PACKET_TYPE                     2
#define SA_COMPLETED_PACKET_TYPE                    3
#define SA_STATUS_PACKET_TYPE                       4
#define SA_ANGLE_PACKET_TYPE                        5
#define SA_VOLTAGE_LEVEL_PACKET_TYPE                6
#define SA_SENSOR_TYPE_PACKET_TYPE                  7
#define SA_SENSOR_ENABLED_PACKET_TYPE               8
#define SA_END_EFFECTOR_TYPE_PACKET_TYPE            9
#define SA_GRIPPER_OPENING_PACKET_TYPE              10
#define SA_FORCE_PACKET_TYPE                        11
#define SA_MOVE_SPEED_PACKET_TYPE                   12
#define SA_PHYSICAL_POSITION_KNOWN_PACKET_TYPE      13
#define SA_POSITION_LIMIT_PACKET_TYPE               14
#define SA_ANGLE_LIMIT_PACKET_TYPE                  15
#define SA_SAFE_DIRECTION_PACKET_TYPE               16
#define SA_SCALE_PACKET_TYPE                        17
#define SA_MOVE_ACCELERATION_PACKET_TYPE            18
#define SA_CHANNEL_PROPERTY_PACKET_TYPE             19
#define SA_CAPTURE_BUFFER_PACKET_TYPE               20
#define SA_TRIGGERED_PACKET_TYPE                    21
#define SA_INVALID_PACKET_TYPE                      255

// channel status codes
#define SA_STOPPED_STATUS                           0
#define SA_STEPPING_STATUS                          1
#define SA_SCANNING_STATUS                          2
#define SA_HOLDING_STATUS                           3
#define SA_TARGET_STATUS                            4
#define SA_MOVE_DELAY_STATUS                        5
#define SA_CALIBRATING_STATUS                       6
#define SA_FINDING_REF_STATUS                       7
#define SA_OPENING_STATUS                           8

// compatibility definitions
#define SA_NO_REPORT_ON_COMPLETE                    0
#define SA_REPORT_ON_COMPLETE                       1

#ifdef __cplusplus
extern "C" {
#endif


/*******************
* Helper Functions *
*******************/
// Decode Selector Value (for some property keys)
MCSCONTROL_API
void MCSCONTROL_CC SA_DSV(signed int value, unsigned int *selector, unsigned int *subSelector);

// Encode Property Key (for SA_SetChannelProperty_X and SA_GetChannelProperty_X)
MCSCONTROL_API
unsigned int MCSCONTROL_CC SA_EPK(unsigned int selector, unsigned int subSelector, unsigned int property);

// Encode Selector Value (for some property keys)
MCSCONTROL_API
signed int MCSCONTROL_CC SA_ESV(unsigned int selector, unsigned int subSelector);

// Transform status code into human readable string
MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetStatusInfo(SA_STATUS status, const char **info);


/**********************
General note:
All functions have a return value of SA_STATUS
indicating success (SA_OK) or failure of execution. See the above
definitions for a list of error codes.
***********************/

/************************************************************************
*************************************************************************
**                 Section I: Initialization Functions                 **
*************************************************************************
************************************************************************/

/* new style initialization functions */

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_OpenSystem(SA_INDEX *systemIndex,const char *locator,const char *options);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_CloseSystem(SA_INDEX systemIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_FindSystems(const char *options,char *outBuffer,unsigned int *ioBufferSize);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetSystemLocator(SA_INDEX systemIndex,char *outBuffer,unsigned int *ioBufferSize);



/* old style initialization functions */

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_AddSystemToInitSystemsList(unsigned int systemId);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_ClearInitSystemsList(void);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetAvailableSystems(unsigned int *idList, unsigned int *idListSize);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_InitSystems(unsigned int configuration);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_ReleaseSystems(void);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetInitState(unsigned int *initMode);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetNumberOfSystems(unsigned int *number);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetSystemID(SA_INDEX systemIndex, unsigned int *systemId);

/* --- */

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetChannelType(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *type);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetDLLVersion(unsigned int *version);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetNumberOfChannels(SA_INDEX systemIndex, unsigned int *channels);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_SetHCMEnabled(SA_INDEX systemIndex, unsigned int enabled);



/************************************************************************
*************************************************************************
**        Section IIa:  Functions for SYNCHRONOUS communication        **
*************************************************************************
************************************************************************/

/*************************************************
**************************************************
**    Section IIa.1: Configuration Functions    **
**************************************************
*************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetAngleLimit_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *minAngle, signed int *minRevolution, unsigned int *maxAngle, signed int *maxRevolution);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetChannelProperty_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int key, signed int *value);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetClosedLoopMoveAcceleration_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *acceleration);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetClosedLoopMoveSpeed_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *speed);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetEndEffectorType_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *type, signed int *param1, signed int *param2);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPositionLimit_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int *minPosition, signed int *maxPosition);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetSafeDirection_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *direction);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetScale_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int *scale, unsigned int *inverted);

MCSCONTROL_API // Global
SA_STATUS MCSCONTROL_CC SA_GetSensorEnabled_S(SA_INDEX systemIndex, unsigned int *enabled);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetSensorType_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *type);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetAccumulateRelativePositions_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int accumulate);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetAngleLimit_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int minAngle, signed int minRevolution, unsigned int maxAngle, signed int maxRevolution);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetChannelProperty_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int key, signed int value);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMaxFrequency_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int frequency);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMoveAcceleration_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int acceleration);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMoveSpeed_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int speed);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_SetEndEffectorType_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int type, signed int param1, signed int param2);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetPosition_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int position);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetPositionLimit_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int minPosition, signed int maxPosition);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetSafeDirection_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int direction);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetScale_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int scale, unsigned int inverted);

MCSCONTROL_API // Global
SA_STATUS MCSCONTROL_CC SA_SetSensorEnabled_S(SA_INDEX systemIndex, unsigned int enabled);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetSensorType_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int type);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetStepWhileScan_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int step);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_SetZeroForce_S(SA_INDEX systemIndex, SA_INDEX channelIndex);

/*************************************************
**************************************************
**  Section IIa.2: Movement Control Functions   **
**************************************************
*************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_CalibrateSensor_S(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_FindReferenceMark_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int direction, unsigned int holdTime, unsigned int autoZero);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoAngleAbsolute_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int angle, signed int revolution, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoAngleRelative_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int angleDiff, signed int revolutionDiff, unsigned int holdTime);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperForceAbsolute_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int force, unsigned int speed, unsigned int holdTime);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperOpeningAbsolute_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int opening, unsigned int speed);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperOpeningRelative_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int speed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoPositionAbsolute_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int position, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoPositionRelative_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_ScanMoveAbsolute_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int target, unsigned int scanSpeed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_ScanMoveRelative_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int scanSpeed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_StepMove_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int steps, unsigned int amplitude, unsigned int frequency);

MCSCONTROL_API // Positioner, End effector
SA_STATUS MCSCONTROL_CC SA_Stop_S(SA_INDEX systemIndex, SA_INDEX channelIndex);

/************************************************
*************************************************
**  Section IIa.3: Channel Feedback Functions  **
*************************************************
*************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetAngle_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *angle, signed int *revolution);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetCaptureBuffer_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int bufferIndex, SA_PACKET *buffer);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetForce_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int *force);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetGripperOpening_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *opening);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPhysicalPositionKnown_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *known);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPosition_S(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int *position);

MCSCONTROL_API // Positioner, End effector
SA_STATUS MCSCONTROL_CC SA_GetStatus_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *status);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetVoltageLevel_S(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int *level);

/************************************************************************
*************************************************************************
**       Section IIb:  Functions for ASYNCHRONOUS communication        **
*************************************************************************
************************************************************************/

/*************************************************
**************************************************
**    Section IIb.1: Configuration Functions    **
**************************************************
*************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_AppendTriggeredCommand_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int triggerSource);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_ClearTriggeredCommandQueue_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_FlushOutput_A(SA_INDEX systemIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetAngleLimit_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetBufferedOutput_A(SA_INDEX systemIndex, unsigned int *mode);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetChannelProperty_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int key);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetClosedLoopMoveAcceleration_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetClosedLoopMoveSpeed_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetEndEffectorType_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPhysicalPositionKnown_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPositionLimit_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetSafeDirection_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetScale_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_GetSensorEnabled_A(SA_INDEX systemIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetSensorType_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetAccumulateRelativePositions_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int accumulate);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetAngleLimit_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int minAngle, signed int minRevolution, unsigned int maxAngle, signed int maxRevolution);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_SetBufferedOutput_A(SA_INDEX systemIndex, unsigned int mode);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetChannelProperty_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int key, signed int value);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMaxFrequency_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int frequency);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMoveAcceleration_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int acceleration);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetClosedLoopMoveSpeed_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int speed);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_SetEndEffectorType_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int type, signed int param1, signed int param2);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetPosition_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int position);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetPositionLimit_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int minPosition, signed int maxPosition);

MCSCONTROL_API // Positioner, End effector
SA_STATUS MCSCONTROL_CC SA_SetReportOnComplete_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int report);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetReportOnTriggered_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int report);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetSafeDirection_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int direction);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetScale_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int scale, unsigned int inverted);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_SetSensorEnabled_A(SA_INDEX systemIndex, unsigned int enabled);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetSensorType_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int type);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_SetStepWhileScan_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int step);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_SetZeroForce_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

/*************************************************
**************************************************
**  Section IIb.2: Movement Control Functions   **
**************************************************
*************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_CalibrateSensor_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_FindReferenceMark_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int direction, unsigned int holdTime, unsigned int autoZero);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoAngleAbsolute_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int angle, signed int revolution, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoAngleRelative_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int angleDiff, signed int revolutionDiff, unsigned int holdTime);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperForceAbsolute_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int force, unsigned int speed, unsigned int holdTime);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperOpeningAbsolute_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int opening, unsigned int speed);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GotoGripperOpeningRelative_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int speed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoPositionAbsolute_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int position, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GotoPositionRelative_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int holdTime);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_ScanMoveAbsolute_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int target, unsigned int scanSpeed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_ScanMoveRelative_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int diff, unsigned int scanSpeed);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_StepMove_A(SA_INDEX systemIndex, SA_INDEX channelIndex, signed int steps, unsigned int amplitude, unsigned int frequency);

MCSCONTROL_API // Positioner, End effector
SA_STATUS MCSCONTROL_CC SA_Stop_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_TriggerCommand_A(SA_INDEX systemIndex, unsigned int triggerIndex);

/************************************************
*************************************************
**  Section IIb.3: Channel Feedback Functions  **
*************************************************
************************************************/
MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetAngle_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetCaptureBuffer_A(SA_INDEX systemIndex, SA_INDEX channelIndex, unsigned int bufferIndex);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetForce_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // End effector
SA_STATUS MCSCONTROL_CC SA_GetGripperOpening_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetPosition_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner, End effector
SA_STATUS MCSCONTROL_CC SA_GetStatus_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

MCSCONTROL_API // Positioner
SA_STATUS MCSCONTROL_CC SA_GetVoltageLevel_A(SA_INDEX systemIndex, SA_INDEX channelIndex);

/******************
* Answer retrieval
******************/
MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_DiscardPacket_A(SA_INDEX systemIndex);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_LookAtNextPacket_A(SA_INDEX systemIndex, unsigned int timeout, SA_PACKET *packet);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_ReceiveNextPacket_A(SA_INDEX systemIndex, unsigned int timeout, SA_PACKET *packet);

MCSCONTROL_API
SA_STATUS MCSCONTROL_CC SA_CancelWaitForPacket_A(SA_INDEX systemIndex);



#ifdef __cplusplus
}
#endif

#endif /* MCSCONTROL_H */
