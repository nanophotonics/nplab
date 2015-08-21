/*****************************************************************************/
/**************** PTG SUPPORT: A PVCAM OPTION LIBRARY *****************/
/*****************************************************************************/
/***** Copyright (C) Roper Scientific, Inc. 2002.  All rights reserved. ******/
/*               Princeton Instruments/Acton 2006.  All rights reserved.     */
/*****************************************************************************/
/*
 * The functions in this library depend upon and make calls to the functions
 * in the regular PVCAM library.  Because of that, this requires the PVCAM
 * library to be present.  This file should be included after the include
 * files "master.h" and "pvcam.h".
 *

  =========================================================================
  Version History:
  -------------------------------------------------------------------------
  Version 1.0.0 
    Original

  Version 2.0.0
    1. Support USB interfaced cameras
    2. Support PI-Max II DIF mode
    3. Eliminate implicit camera controls

      In order for PTG to be active and work properly with the version 2,
      the application must explicitly program the camera to certain conditions:

      Exposure mode through functions, pl_exp_setup_cont() or pl_exp_setup_seq()
        INT_STROBE_MODE (internal sync via PTG)
        BULB_MODE or STROBED_MODE (DIF)

      PARAM_CONT_CLEARS with 
        FALSE -- Disable Continuous Cleans

      PARAM_SHTR_OPEN_MODE 
        OPEN_PRE_TRIGGER  -- PreOpen true

      PARAM_EDGE_TRIGGER  
        EDGE_TRIG_POS for DIF 
        EDGE_TRIG_NEG other readout mode


 *****************************************************************************/
#ifndef _PVCAM_PTG_H
#define _PVCAM_PTG_H


/********************************* CONSTANTS *********************************/



/**************************** FUNCTION PROTOTYPES ****************************/
#ifdef PV_C_PLUS_PLUS                  /* The prevents C++ compilers from    */
extern "C"
{                                      /*   performing "name mangling".      */
#endif

#define CLASS94	94	           /* PTG operations */
#define MAX_PTG_PLUGIN_DESCRIPTION_STRING_LENGTH 80

  /***************************************************************************/
  /***************************************************************************/
  /*                                                                         */
  /* DEVELOPER NOTES:                                                        */
  /*                                                                         */
  /*                                                                         */
  /*    The pl_ff_get_ver routine returns the version number of the plugin.  */
  /*    The format of the unsigned 16 bit number is the following:           */
  /*                       ----- LOW BYTE -----                              */
  /*           HIGH BYTE   HI NIBBLE  LO NIBBLE                              */
  /*           major ver   minor ver  trivial ver                            */
  /*    which makes the ranges for                                           */
  /*           major version (0-255)                                         */
  /*           minor version (0-15)                                          */
  /*           trivial version (0-15)                                        */
  /*                                                                         */
  /***************************************************************************/
  /***************************************************************************/

/* PTG parameters */

/* ####################### */
/* General parameters      */
/* ####################### */

/* Time Units, This sets the timeunits for whole plugin                     */
#define PARAM_PTG_TIME_UNITS ((CLASS94 << 16) + (TYPE_ENUM << 24) + 22)

/* Board temperature, read only in Celsius. (PTG only)                      */
#define PARAM_PTG_TEMPERATURE ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1615)

/* ####################### */
/* Main Trigger parameters */
/* ####################### */

/* Main trigger sets the trigger to internal (default) or external          */
/* (enum main_trigger_modes)                                                */
#define PARAM_PTG_MAIN_TRIGGER      ((CLASS94 << 16) + (TYPE_ENUM << 24) + 11)

/* Internal frequency, this is in Hz                                        */
/* For SprSync, this frequency is used for SyncMASTER frequency             */
#define PARAM_PTG_INT_TRIG_FREQ    ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 12)

/* Ext trigger threshold, this is in volts                                  */
#define PARAM_PTG_EXT_TRIG_THRESH  ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 13)
/* Ext trigger slope (positive or negative), positive is default            */
#define PARAM_PTG_EXT_TRIG_SLOPE    ((CLASS94 << 16) + (TYPE_ENUM << 24) + 14)
/* Ext trigger Termination (either High Z or 50 ohm), High Z default        */
#define PARAM_PTG_EXT_TRIG_TERMINATION ((CLASS94 << 16) + (TYPE_ENUM << 24) + 15)
/* Ext trigger coupling. (AC or DC) default DC coupled                      */
#define PARAM_PTG_EXT_TRIG_COUPLING ((CLASS94 << 16) + (TYPE_ENUM << 24) + 16)

/* ######################### */
/* Timing Pattern parameters */
/* ######################### */

/* On chip Accumulation, number of on-chip accumulations.                   */
#define PARAM_PTG_ON_CHIP_ACCUM ((CLASS94 << 16) + (TYPE_UNS16 << 24) + 1614)

/* Gate Width:
                     Default   Minimum   Maximum   Resolution
       --------------------------------------------------------   
                PTG  1.0 us    0.0 ns    26 ms     0.04 nsec
       SuperSynchro  10 ms     0.01 ns   21 s      1.0 nsec                 */
#define PARAM_PTG_PULSE_WIDTH ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 21)

/* Gate Delay:
                     Default   Minimum   Maximum   Resolution
       --------------------------------------------------------   
                PTG  1.0 us    3.125 ns  26 ms     0.04 nsec
       SuperSynchro  0.01 ns   0.01 ns   21 s      0.01 nsec                */
#define PARAM_PTG_PULSE_DELAY ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 23)

/* Aux Delay:
                     Default   Minimum   Maximum   Resolution
       --------------------------------------------------------   
                PTG  0.0       0.0       26 ms     0.04 nsec
       SuperSynchro  10 ns     0.01 ns   21 s      1.0 nsec                 */
#define PARAM_PTG_AUX_DELAY ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 69)

/* Aux Width:
                     Default   Minimum   Maximum   Resolution
       --------------------------------------------------------   
                PTG  n/a
       SuperSynchro  10 us     0.01 ns   21 s      5.0 nsec                 */
#define PARAM_PTG_AUX_WIDTH ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 71)

/* @@@@@@@@@@@@@@@@@@@ */
/* Advanced operations */
/* @@@@@@@@@@@@@@@@@@@ */

/* ###################### */
/* Burst Trigger Settings */
/* ###################### */

/* Burst period. (def 100 usec, min 12.5 nsec, max 13.4 sec, res 12.5 nsec) */
#define PARAM_PTG_BURST_PERIOD ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 34)
/* Burst count. (def 1, min 1, max 8191, res 1)                             */
#define PARAM_PTG_BURST_COUNT ((CLASS94 << 16) + (TYPE_UNS32 << 24) + 32)
/* Burst Active, set to true to use burst triggers.                         */
#define PARAM_PTG_BURST_ACTIVE ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 33)

/* ####################### */
/* Bracket Settings        */
/* ####################### */
/* Enables/disables bracket. */

#define PARAM_PTG_BRACKET_PULSE ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 9109)

/* ####################### */
/* Anticipator Settings    */
/* ####################### */
/* Anticipator Delay, default 0.0, min 0.0, max 10.0 usec, res 0.1 usec     */
#define PARAM_PTG_ANTICIPATOR_DELAY ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1605)
/* Anticipator Active, set to true to use anticipator for bracket start     */ 
#define PARAM_PTG_ANTICIPATOR_ACTIVE ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 1606)

/* ############################# */
/* Main Trigger Counter Settings */
/* ############################# */
/* Trigger count, this can only be read, not set.                           */
#define PARAM_PTG_TRIGGER_COUNT ((CLASS94 << 16) + (TYPE_INT32 << 24) + 1601)
/* Trigger count type, either main (default) or main burst.                 */
#define PARAM_PTG_TRIGGER_COUNT_TYPE ((CLASS94 << 16) + (TYPE_ENUM << 24) + 1602)

/* #################################################################### */
/* Sequential Gating parameters (common to both Linear and Exponential) */
/* #################################################################### */
/* Gating Mode, default is single shot/continous which uses just one width and delay */
/* for Sequential (linear, exponential, or Custom) you should pick SEQUENTIAL_GATING */
#define PARAM_PTG_GATING_MODE ((CLASS94 << 16) + (TYPE_ENUM << 24) + 901)

/* Sequential Type (default Linear, could also be exponential and Custom). */
#define PARAM_PTG_SEQUENTIAL_TYPE ((CLASS94 << 16) + (TYPE_ENUM << 24) + 103)

/* Sequential number of shots. Default 10, min 1, max 32768 */
#define PARAM_PTG_SEQ_NUM_SHOTS ((CLASS94 << 16) + (TYPE_UNS32 << 24) + 102)
/* Sequential delay start (default 1.0us, min 3.125ns, max 26 ms, resolution 0.04 ns) */
#define PARAM_PTG_SEQ_DELAY_START ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 108)
/* Sequential delay end (default 11.0us, min 3.125ns, max 26 ms, resolution 0.04 ns) */
#define PARAM_PTG_SEQ_DELAY_END ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 110)
/* Sequential width start (default 1.0us, min 0.0 ns, max 26 ms, resolution 0.04 ns) */
#define PARAM_PTG_SEQ_WIDTH_START ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 104)
/* Sequential width end (default 1.0us, min 0.0 ns, max 26 ms, resolution 0.04 ns) */
#define PARAM_PTG_SEQ_WIDTH_END ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 106)


/* ########################################################### */
/* Sequential Gating Exponential parameters (Exponential only) */
/* ########################################################### */
/* Slow Tau (default 10.0 us) */
#define PARAM_PTG_SEQ_SLOW_TIMECONSTANT ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 121)
/* Slow Amplitude (default 10.0) */
#define PARAM_PTG_SEQ_SLOW_AMPLITUDE ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 123)
/* Fast Tau (default 1.0 us) */
#define PARAM_PTG_SEQ_FAST_TIMECONSTANT ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 118)
/* Fast Amplitude (default 1.0) */
#define PARAM_PTG_SEQ_FAST_AMPLITUDE ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 120)


/* ######################## */
/* Sequential Gating Custom */
/* ######################## */

/* Note: PARAM_PTG_SEQ_NUM_SHOTS should be setup first, the following arrays should */
/* be the same size as number of shots.                                             */

/* Sequence Pulse Delay array (array of doubles)                            */
#define PARAM_PTG_SEQ_PULSE_DELAY_ARRAY ((CLASS94 << 16) + (TYPE_VOID_PTR << 24) + 124)
/* Sequence Pulse Width array (array of doubles)                            */
#define PARAM_PTG_SEQ_PULSE_WIDTH_ARRAY ((CLASS94 << 16) + (TYPE_VOID_PTR << 24) + 125)
/* Sequence Aux Delay array (array of doubles)                              */
#define PARAM_PTG_SEQ_AUX_DELAY_ARRAY ((CLASS94 << 16) + (TYPE_VOID_PTR << 24) + 126)
/* Sequence On Chip accumulation array (array of longs)                     */
#define PARAM_PTG_SEQ_ONCHIP_ACCUM_ARRAY ((CLASS94 << 16) + (TYPE_VOID_PTR << 24) + 128)


/* ################################ */
/* DIF gate timing for SuperSynchro */
/* ################################ */

#define PARAM_PTG_DIF1_DELAY      ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1405)
#define PARAM_PTG_DIF1_WIDTH      ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1408)
#define PARAM_PTG_DIF1_AUX_DELAY  ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1411)
#define PARAM_PTG_DIF1_AUX_WIDTH  ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1414)
#define PARAM_PTG_DIF2_DELAY      ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1406)
#define PARAM_PTG_DIF2_WIDTH      ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1409)
#define PARAM_PTG_DIF2_AUX_DELAY  ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1412)
#define PARAM_PTG_DIF2_AUX_WIDTH  ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1415)


/* ####################### */
/* Calibration             */
/* ####################### */
/* Pulse delay from (either ext trigger in or t0 out (default).             */
#define PARAM_PTG_PULSE_DELAY_FROM ((CLASS94 << 16) + (TYPE_ENUM << 24) + 25)
/* Use Calibration active. Set to true to use calibration stored in NvRam.  */
#define PARAM_PTG_USE_CALIB ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 201)

/* ######### */
/* Misc.     */
/* ######### */
/* Enable/Disable trigger output.                                           */
#define PARAM_PTG_TRIGGER_OUTPUT ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 1612)
/* Enable/Disable fast 2ns board */
#define PARAM_FAST_PULSE_ENABLE ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 233)

/* ################### */
/* SyncMaster Specific */
/* ################### */
/* True to enable the Master Clock output */
#define PARAM_PTG_MASTER_CLOCK    ((CLASS94 << 16) + (TYPE_BOOLEAN << 24) + 1401)
/* Master Clock 2 delay from Master Clock in Usec */
#define PARAM_PTG_MASTER2_DELAY   ((CLASS94 << 16) + (TYPE_FLT64 << 24) + 1403)

/* Note: currently the FTG is a special and is not a standard product, these */
/* parameters are meaningless for PTG systems and should not be used.        */
/* ################################ */
/* Trigger Port Settings (FTG Only) */
/* ################################ */

/* ################################ */
/* Gate Channel Settings (FTG Only) */
/* ################################ */

/* ############################################################################### */
/* Enumerated types for PTG/FTG                                                    */
/* ############################################################################### */
/* ####################### */
/* General Enums           */
/* ####################### */
/* Time units */
/* used by PARAM_PTG_TIME_UNITS */
enum TimeUnits
{
    PTG_TimeUnit_USEC = 1,
    PTG_TimeUnit_MSEC,
    PTG_TimeUnit_SEC,
    PTG_TimeUnit_MIN,
    PTG_TimeUnit_HOUR,
    PTG_TimeUnit_FRAMES,
    PTG_TimeUnit_NSEC,
    PTG_TimeUnit_PSEC
};

/* Pulsar type is used with pl_ptg_init_plugin */
enum PulsarTypes
{
    PTG_NONE     = 0,
    PTG          = 2,
    FTG          = 4,
    SUPERSYNCHRO = 5
};


/* ####################### */
/* Main Trigger Enums      */
/* ####################### */

/* used with PARAM_PTG_MAIN_TRIGGER */
enum main_trigger_modes
{                               /* PTG   SprSync */
  PTG_USE_INTERNAL_TRIG = 0,    /*  x     x      */
  PTG_USE_EXTERNAL_TRIG,        /*  x     x      */
  PTG_USE_SINGLESHOT,           /*  x            */
  PTG_USE_SINGLESHOT_INTERNAL   /*  x            */
};

/* used with PARAM_PTG_EXT_TRIG_SLOPE */
enum ptg_slope
{
  PTG_NEGATIVE_SLOPE = 0,
  PTG_POSITIVE_SLOPE
};

/* used with PARAM_PTG_EXT_TRIG_TERMINATION */
enum ptg_termination_modes
{
  PTG_FIFTY_OHMS = 0,
  PTG_HIGH_Z
};

/* used with PARAM_PTG_EXT_TRIG_COUPLING */
enum ptg_coupling_modes
{
  PTG_AC_COUPLED = 0,
  PTG_DC_COUPLED
};


/* ############################# */
/* Main Trigger Counter Settings */
/* ############################# */
/* used with PARAM_PTG_TRIGGER_COUNT_TYPE */
enum ptg_count_type
{
  PTG_TRIGCNT_MAIN  = 1,
  PTG_TRIGCNT_MAIN_BURST
};

/* #################################################################### */
/* Sequential Gating parameters (common to both Linear and Exponential) */
/* #################################################################### */

/* used with PARAM_PTG_GATING_MODE to define continous gating or sequential gating  */
/* sequential gating is were either the width and/or the delay change during the */
/* experiment. There is three ways of doing this linear, exponetial, or custom   */
enum ptg_gate_mode_type
{
    PTG_CONTINOUS_GATING = 0,
    PTG_SEQUENTIAL_GATING
};

/* used by PARAM_PTG_SEQUENTIAL_TYPE. If gate mode is set to sequential then this */
/* param sets what type of sequential (linear, exponetial, or custom).            */
enum ptg_seq_type
{
    PTG_SEQ_LINEAR = 0,
    PTG_SEQ_EXPONENTIAL,
    PTG_SEQ_CUSTOM
};


/* ####################### */
/* Calibration Enums       */
/* ####################### */
enum ptg_delay_from_modes
{
  PTG_DEL_FROM_EXT_TRIG_IN = 1601,
  PTG_DEL_FROM_T0_OUT
};



/* ############################################################################### */
/* Exported Functions for PTG plugin                                               */
/* ############################################################################### */

/* get description of plugin. */
boolean PV_DECL pl_ptg_get_plugin_description ( char_ptr plugin_description );

/* get plugin version */
boolean PV_DECL pl_ptg_get_ver ( uns16_ptr version );

/* initialize plugin and load any needed DLLs, allocate any needed resources. */
boolean PV_DECL pl_ptg_init_plugin (int16 hcam, int32 PulsarType);

/* Same as above, but the function auto-detect the Pulser type and give it to the caller */
boolean PV_DECL pl_ptg_init_plugin_auto_detect (int16 hcam, int32 *PulserType);


/* unitialize plugin, unload any loaded dlls and free resources. */
boolean PV_DECL pl_ptg_uninit_plugin (int16 hcam);

/* give error code return ASCII string */
boolean PV_DECL pl_ptg_error_message (int16 err_code, char_ptr msg);

/* Get last error code. */
int16 PV_DECL   pl_ptg_error_code(void);

/* Get different attributes of a given parameter id. These are defined in pvcam_ptg.h */
/* attributes are defined in pvcam.h */
boolean PV_DECL pl_ptg_get_param( int16 hcam, 
                                  uns32 param_id, 
                                  int16 param_attribute,
					                        void_ptr param_value   );

/* set a parameter id with a value. parameter ids are in pvcam_ptg.h */
boolean PV_DECL pl_ptg_set_param( int16 hcam, 
                                  uns32 param_id, 
                                  void_ptr param_value );

/* gvien an parameter id (that is an enum type) and an index, return enumerated type */
/* and ASCII string that defines the enumerated type.                                */
boolean PV_DECL pl_ptg_get_enum_param ( int16 hcam, 
                                        int32 param_id, 
                                        uns32 index,
					    			                    int32_ptr value, 
                                        char_ptr desc, 
                                        uns32 length     );

/* Download and initialize the PTG board for data collection */
boolean PV_DECL pl_ptg_initialize(int16 hcam);

/* Start the PTG for data collection (this should come before the camera/pvcam start */
boolean PV_DECL pl_ptg_start (int16 hcam);

/* Stop the PTG, this should come after the stop for the camera. */
boolean PV_DECL pl_ptg_stop (int16 hcam);

/* Reset counter in PTG. */
boolean PV_DECL pl_ptg_reset (int16 hcam);



/* ####################### */
/* Error Code              */
/* ####################### */
#define CLASS94_ERROR 9400      /* PTG may use errors 9400 - 9499   */

enum c94_error_vals
{
  C94_VC_UNKNOWN_ERROR = CLASS94_ERROR, /* PTG OPTION LIBRARY:       */
                                        /* unknown error                      */
  C94_NOT_AVAILABLE,
  C94_ATTRIBUTE_INVALID,
  C94_BAD_CONTROLLER,
  C94_PARAM_NOT_DEFINED,
  C94_DATATYPE_NOTSUPPORTED,
  C94_NOT_INITIALIZED,
  C94_CNTRL_INIT_FAILED,
  C94_INTERNAL_FAIL,
  C94_ILLEGAL_ENUM_VALUE,
  C94_ILLEGAL_CAMERA_HANDLE,
  C94_UNSUPPORTED_CAMERA,
  C94_READONLY_PARAM,
  C94_FAILED_TO_SET_VALUE,
  C94_ILLEGAL_VALUE,
  C94_END
};


#ifdef PV_C_PLUS_PLUS
};
#endif

#endif /* _PV_PTG_H */
