/*****************************************************************************/
/**************** EMCalib: A PVCAM Option Library ****************************/
/*****************************************************************************/
/***** Copyright (C) Roper Scientific, Inc. 2002.  All rights reserved. ******/
/*               Princeton Instruments 2009.  All rights reserved.           */
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

 *****************************************************************************/
#ifndef _PVCAM_EMCALIB_H
#define _PVCAM_EMCALIB_H


#ifdef PV_C_PLUS_PLUS
extern "C"
{
#endif

#define CLASS90	90	           /* EM Calibration */
#define MAX_EMC_PLUGIN_DESCRIPTION_STRING_LENGTH 80

  /***************************************************************************/
  /***************************************************************************/
  /*                                                                         */
  /* DEVELOPER NOTES:                                                        */
  /*                                                                         */
  /*                                                                         */
  /*    The pl_emc_get_ver routine returns the version number of the plugin. */
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


/* ######################################################################### */
/* EMCalib Parameters                                                        */
/* ######################################################################### */

/* date of last calibration: value is year + day*1e4 + month*1e6: get only   */
#define PARAM_EMC_DATE              ((CLASS90<<16) + (TYPE_UNS32<<24)      + 1)
/* actual temperature of the detector in 10 * Deg C: get only                */
#define PARAM_EMC_TEMP              ((CLASS90<<16) + (TYPE_INT16<<24)      + 2)
/* desired temperature of the detector in 10 * Deg C                         */
#define PARAM_EMC_TEMP_SETPOINT     ((CLASS90<<16) + (TYPE_INT16<<24)      + 3)
/* desired temperature of the detector has stabilized                        */
#define PARAM_EMC_TEMP_LOCKED       ((CLASS90<<16) + (TYPE_BOOLEAN<<24)    + 4)


/* ######################################################################### */
/* EMCalib Types                                                             */
/* ######################################################################### */
/* optional callback during calibration                                      */
/* reports progress as percentage from 0-100                                 */
/* allows cancelation: return PV_FAIL to cancel or PV_OK to proceed          */
typedef rs_bool (__stdcall* emc_in_progress_callback) (int16 emc_hcam,
                                                       int32 progress,
                                                       void_ptr user_state );

/* ######################################################################### */
/* EMCalib Exported Functions                                                */
/* ######################################################################### */
/* get description of plugin                                                 */
rs_bool PV_DECL pl_emc_get_plugin_description (char_ptr plugin_description);
/* get plugin version                                                        */
rs_bool PV_DECL pl_emc_get_ver (uns16_ptr version);
/* initialize plugin                                                         */
rs_bool PV_DECL pl_emc_init_plugin (void);
/* uninitialize plugin                                                       */
rs_bool PV_DECL pl_emc_uninit_plugin (void);
/* get last plugin error code                                                */
int16 PV_DECL pl_emc_error_code (void);
/* give error code return ASCII string                                       */
rs_bool PV_DECL pl_emc_error_message (int16 err_code, char_ptr msg);
/* opens camera via name and returns emc camera handle                       */
rs_bool PV_DECL pl_emc_cam_open (char_const_ptr camera_name,
                                 int16_ptr emc_hcam);
/* closes emc camera handle                                                  */
rs_bool PV_DECL pl_emc_cam_close (int16 emc_hcam);
/* get different attributes of a given parameter id                          */
/* attributes are defined in pvcam.h                                         */
rs_bool PV_DECL pl_emc_get_param (int16 emc_hcam, 
                                  uns32 param_id, 
                                  int16 param_attribute,
					              void_ptr param_value);
/* set a parameter id with a value                                           */
rs_bool PV_DECL pl_emc_set_param (int16 emc_hcam,
                                  uns32 param_id,
                                  void_ptr param_value);
/* runs calibration and returns when completed, canceled or an error occurs  */
/* detector temperature must be locked before calibrating                    */
/* callback is optional and supports progress and cancelation                */
rs_bool PV_DECL pl_emc_calibrate (int16 emc_hcam,
                                  emc_in_progress_callback callback,
                                  void_ptr user_state);
                                  


/* ######################################################################### */
/* Error Codes                                                               */
/* ######################################################################### */
#define CLASS90_ERROR 9000      /* EMCalib may use errors 9000 - 9099 */

enum c90_error_vals
{
    C90_UNKNOWN_ERROR = CLASS90_ERROR,
    C90_EMC_NOT_INITED,
    C90_EMC_ALREADY_INITED,
    C90_NULL_POINTER,
    C90_OUT_OF_RANGE,
    C90_CAMERA_NOT_SUPPORTED,
    C90_INVALID_HANDLE,
    C90_PARAMETER_INVALID,
    C90_ATTRIBUTE_INVALID,
    C90_PARAM_READONLY,
    C90_TEMP_NOT_LOCKED,
    C90_CALIBRATION_CANCELED,
    C90_END
};


#ifdef PV_C_PLUS_PLUS
};
#endif

#endif /* _PVCAM_EMCALIB_H */
