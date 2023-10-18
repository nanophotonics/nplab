/******************************************************************************/
/* TsiCamera.h                                                                */
/*----------------------------------------------------------------------------*/
/*                                                                            */
/******************************************************************************/
#ifndef __THORLABS_SCIENTIFIC_IMAGING_CAMERA_H__
#define __THORLABS_SCIENTIFIC_IMAGING_CAMERA_H__

#define TSI_CAMERA_VERSION 0x00000105

#define TSI_WAIT_INFINITE -1 

#include "platform_specific.h"
#include "TsiError.h"

//------------------------------------------------------------------------------
// TSI attribute types.
//------------------------------------------------------------------------------
typedef enum _TSI_ATTR_ID  
{

   TSI_ATTR_NAME          ,
   TSI_ATTR_DATA_TYPE     ,
   TSI_ATTR_ARRAY_COUNT   ,
   TSI_ATTR_FLAGS         ,
   TSI_ATTR_MIN_VALUE     ,
   TSI_ATTR_MAX_VALUE     ,
   TSI_ATTR_DEFAULT_VALUE ,
   TSI_MAX_ATTR 

} TSI_ATTR_ID, *PTSI_ATTR_ID;


//------------------------------------------------------------------------------
// TSI data types.
//------------------------------------------------------------------------------
typedef enum _TSI_DATA_TYPE
{
   TSI_TYPE_NONE  ,
   TSI_TYPE_UNS8  ,
   TSI_TYPE_UNS16 ,
   TSI_TYPE_UNS32 ,
   TSI_TYPE_UNS64 ,
   TSI_TYPE_INT8  ,
   TSI_TYPE_INT16 ,
   TSI_TYPE_INT32 ,
   TSI_TYPE_INT64 ,
   TSI_TYPE_TEXT  ,
   TSI_TYPE_FP    ,
   TSI_MAX_TYPES

} TSI_DATA_TYPE;


//------------------------------------------------------------------------------
// TSI data flags.
//------------------------------------------------------------------------------
typedef enum _TSI_PARAM_FLAGS 
{

   TSI_FLAG_READ_ONLY           = 0x00000001 ,
   TSI_FLAG_WRITE_ONLY          = 0x00000002 ,
   TSI_FLAG_UNSUPPORTED         = 0x00000004 , 
   TSI_FLAG_VALUE_CHANGED       = 0x00000008 

} TSI_PARAM_FLAGS;

//------------------------------------------------------------------------------
// TSI parameters.
//------------------------------------------------------------------------------
typedef enum _TSI_PARAM_ID
{
   TSI_PARAM_CMD_ID_ATTR_ID                 = 0,  // 0
   TSI_PARAM_ATTR                           = 1,  // 1
   TSI_PARAM_PROTOCOL                       = 2,  // 2
   TSI_PARAM_FW_VER                         = 3,  // 3
   TSI_PARAM_HW_VER                         = 4,  // 4
   TSI_PARAM_HW_MODEL                       = 5,  // 5
   TSI_PARAM_HW_SER_NUM                     = 6,  // 6
   TSI_PARAM_CAMSTATE                       = 7,  // 7
   TSI_PARAM_CAM_EXPOSURE_STATE             = 8,  // 8
   TSI_PARAM_CAM_TRIGGER_STATE              = 9,  // 9
   TSI_PARAM_EXPOSURE_UNIT                  = 10,  // 10
   TSI_PARAM_EXPOSURE_TIME                  = 11,  // 11
   TSI_PARAM_ACTUAL_EXPOSURE_TIME           = 12,  // 12
   TSI_PARAM_HSIZE                          = 13,  // 13
   TSI_PARAM_VSIZE                          = 14,  // 14
   TSI_PARAM_ROI_BIN                        = 15,  // 15
   TSI_PARAM_FRAME_COUNT                    = 16,  // 16
   TSI_PARAM_CURRENT_FRAME                  = 17,  // 17
   TSI_PARAM_OP_MODE                        = 18,  // 18
   TSI_PARAM_CDS_GAIN_INDEX                 = 19,  // 19
   TSI_PARAM_CDS_GAIN = TSI_PARAM_CDS_GAIN_INDEX, // 19
   TSI_PARAM_VGA_GAIN                       = 20,  // 20
   TSI_PARAM_GAIN                           = 21,  // 21
   TSI_PARAM_OPTICAL_BLACK_LEVEL            = 22,  // 22
   TSI_PARAM_PIXEL_OFFSET                   = 23,  // 23
   TSI_PARAM_READOUT_SPEED_INDEX            = 24,  // 24
   TSI_PARAM_READOUT_SPEED                  = 25,  // 25
   TSI_PARAM_FRAME_TIME                     = 26,  // 26
   TSI_PARAM_FRAME_RATE                     = 27,  // 27
   TSI_PARAM_COOLING_MODE                   = 28,  // 28
   TSI_PARAM_COOLING_SETPOINT               = 29,  // 29
   TSI_PARAM_TEMPERATURE                    = 30,  // 30 - NOT SUPPORTED.  DO NOT USE.
   TSI_PARAM_QX_OPTION_MODE                 = 31,  // 31 
   TSI_PARAM_TURBO_MODE	                    = 32,  // 32
   TSI_PARAM_TURBO_CODE_MODE = TSI_PARAM_TURBO_MODE, // 32
   TSI_PARAM_XORIGIN                        = 33,  // 33
   TSI_PARAM_YORIGIN                        = 34,  // 34
   TSI_PARAM_XPIXELS                        = 35,  // 35
   TSI_PARAM_YPIXELS                        = 36,  // 36
   TSI_PARAM_XBIN                           = 37,  // 37
   TSI_PARAM_YBIN                           = 38,  // 38
   TSI_PARAM_IMAGE_ACQUISTION_MODE          = 39,  // 39
   TSI_PARAM_NAMED_VALUE                    = 40,  // 40
   TSI_PARAM_TAPS_INDEX                     = 41,  // 41
   TSI_PARAM_TAPS_VALUE                     = 42,  // 42
   TSI_PARAM_RESERVED_1                     = 43,  // 43
   TSI_PARAM_RESERVED_2                     = 44,  // 44
   TSI_PARAM_RESERVED_3                     = 45,  // 45
   TSI_PARAM_RESERVED_4                     = 46,  // 46
   TSI_PARAM_GLOBAL_CAMERA_NAME             = 47,  // 47
   TSI_PARAM_CDS_GAIN_VALUE                 = 48,  // 48
   TSI_PARAM_PIXEL_SIZE                     = 49,  // 49
   TSI_PARAM_BITS_PER_PIXEL                 = 50,  // 50
   TSI_PARAM_BYTES_PER_PIXEL                = 51,  // 51
   TSI_PARAM_READOUT_TIME                   = 52,  // 52
   TSI_PARAM_HW_TRIGGER_ACTIVE              = 53,  // 53
   TSI_PARAM_HW_TRIG_SOURCE                 = 54,  // 54
   TSI_PARAM_HW_TRIG_POLARITY               = 55,  // 55
   TSI_PARAM_TAP_BALANCE_ENABLE             = 56,  // 56
   TSI_PARAM_DROPPED_FRAMES                 = 57,  // 57
   TSI_PARAM_EXPOSURE_TIME_US               = 58,  // 58        

   //---------------------------------------------------------------------------
   TSI_PARAM_RESERVED_5                     = 59,  // 59 - TDI_LINE_SHIFT_TIME
   TSI_PARAM_RESERVED_6                     = 60,  // 60 - TDI_LINE_READ_TIME
   TSI_PARAM_RESERVED_7                     = 61,  // 61 - TSI_PARAM_TDI_AUTO_FOCUS_ENABLE
   //---------------------------------------------------------------------------

   TSI_PARAM_UPDATE_PARAMETERS              = 62,  // 62
   TSI_PARAM_FEATURE_LIST                   = 63,  // 63
   TSI_PARAM_FEATURE_VALID                  = 64,  // 64
   TSI_PARAM_NUM_IMAGE_BUFFERS              = 65,  // 65
   TSI_PARAM_COLOR_FILTER_TYPE              = 66,  // 66
   TSI_PARAM_COLOR_FILTER_PHASE             = 67,  // 67
   TSI_PARAM_COLOR_IR_FILTER_TYPE           = 68,  // 68
   TSI_PARAM_COLOR_CAMERA_CORRECTION_MATRIX = 69,  // 69
   TSI_PARAM_CCM_OUTPUT_COLOR_SPACE         = 70,  // 70
   TSI_PARAM_DEFAULT_WHITE_BALANCE_MATRIX   = 71,  // 71
   TSI_PARAM_USB_ENABLE_LED                 = 72,  // 72
   TSI_MAX_PARAMS                           = 73,  // 73

   // TODO: TSI_PARAM_IMAGE_MANAGER_PTR // Returns object.
   // TODO: TSI_PARAM_APPLY_CHANGES - (CALC)
   // TODO: TSI_PARAM_PIXEL_BUFFER_SIZE_IN_BYTES
   // TODO: TSI_PARAM_USER_PIXEL_BUFFER_NUM_IMAGES
   // TODO: TSI_PARAM_USER_PIXEL_BUFFER_PTR

} TSI_PARAM_ID;

//------------------------------------------------------------------------------
// TSI Camera Status 
//------------------------------------------------------------------------------
typedef enum _TSI_CAMERA_STATUS
{
   TSI_STATUS_CLOSED ,
   TSI_STATUS_OPEN   ,
   TSI_STATUS_BUSY   ,
   TSI_STATUS_MAX

} TSI_CAMERA_STATUS;


//------------------------------------------------------------------------------
// TSI Camera Control Callback Events.
//------------------------------------------------------------------------------
typedef enum _TSI_CAMERA_CONTROL_EVENT_ID
{
   TSI_CAMERA_CONTROL_EXPOSURE_START    ,
   TSI_CAMERA_CONTROL_EXPOSURE_COMPLETE ,
   TSI_CAMERA_CONTROL_SEQUENCE_START    ,
   TSI_CAMERA_CONTROL_SEQUENCE_COMPLETE ,
   TSI_CAMERA_CONTROL_READOUT_START     ,
   TSI_CAMERA_CONTROL_READOUT_COMPLETE  ,
   TSI_CAMERA_CONTROL_DISCONNECT        ,
   TSI_CAMERA_CONTROL_RECONNECT         ,
   TSI_MAX_CAMERA_CONTROL_EVENT_ID

} TSI_CAMERA_CONTROL_EVENT_ID;


//------------------------------------------------------------------------------
// TSI Image Notification Callback Events.
//------------------------------------------------------------------------------
typedef enum _TSI_IMAGE_NOTIFICATION_EVENT_ID
{
   TSI_IMAGE_NOTIFICATION_PENDING_IMAGE,
   TSI_IMAGE_NOTIFICATION_ACQUISITION_ERROR,
   TSI_MAX_IMAGE_NOTIFICATION_EVENT_ID

} TSI_IMAGE_NOTIFICATION_EVENT_ID;



//------------------------------------------------------------------------------
// TSI Image Acquisition Status 
//------------------------------------------------------------------------------
typedef enum _TSI_ACQ_STATUS_ID
{
   TSI_ACQ_STATUS_IDLE               ,
   TSI_ACQ_STATUS_WAITNG_FOR_TRIGGER ,
   TSI_ACQ_STATUS_EXPOSING           ,
   TSI_ACQ_STATUS_READING_OUT        ,
   TSI_ACQ_STATUS_DONE               ,
   TSI_ACQ_STATUS_ERROR              ,
   TSI_ACQ_STATUS_TIMEOUT            ,
   TSI_MAX_ACQ_STATUS_ID

} TSI_ACQ_STATUS_ID;


//------------------------------------------------------------------------------
// TSI Image Acquisition Modes 
//------------------------------------------------------------------------------
typedef enum _TSI_IMAGE_MODES
{
   TSI_IMAGE_MODE_ALLOCATE ,
   TSI_IMAGE_MODE_STREAM   ,
   TSI_IMAGE_MODE_TRIGGER  ,
   TSI_MAX_IMAGE_MODES

} TSI_IMAGE_ACQUISTION_MODES;


//------------------------------------------------------------------------------
// TSI Region of interest structure.
//------------------------------------------------------------------------------
typedef struct _TSI_ROI_BIN 
{
   uint32_t XOrigin;
   uint32_t YOrigin;
   uint32_t XPixels;
   uint32_t YPixels;
   uint32_t XBin;
   uint32_t YBin;

} TSI_ROI_BIN, *PTSI_ROI_BIN;


//------------------------------------------------------------------------------
// TSI Hardware Trigger Control
//------------------------------------------------------------------------------
typedef enum _TSI_HW_TRIG_SOURCE 
{
   TSI_HW_TRIG_OFF,
   TSI_HW_TRIG_AUX,
   TSI_HW_TRIG_CL,
   TSI_HW_TRIG_MAX
} TSI_HW_TRIG_SOURCE, *PTSI_HW_TRIG_SOURCE;

typedef enum _TSI_HW_TRIG_POLARITY 
{
   TSI_HW_TRIG_ACTIVE_HIGH,
   TSI_HW_TRIG_ACTIVE_LOW,
   TSI_HW_TRIG_POL_MAX
} TSI_HW_TRIG_POLARITY, *PTSI_HW_TRIG_POLARITY;	

//------------------------------------------------------------------------------
// TSI Color filter array phase values
//------------------------------------------------------------------------------
enum TSI_COLOR_FILTER_ARRAY_PHASE_VALUES
{
   CFA_PHASE_NOT_SUPPORTED,
   BAYER_RED,
   BAYER_BLUE,
   BAYER_GREEN_LEFT_OF_RED,
   BAYER_GREEN_LEFT_OF_BLUE
};

//------------------------------------------------------------------------------
// TSI ParameterID/AttributeID for Parameter discovery
//------------------------------------------------------------------------------
typedef struct _TSI_PARAM_ATTR_ID 
{
   TSI_PARAM_ID  ParamID;
   TSI_ATTR_ID   AttrID;

} TSI_PARAM_ATTR_ID, *PTSI_PARAM_ATTR_ID;



//------------------------------------------------------------------------------
// TSI ParameterID/AttributeID for Parameter discovery
//------------------------------------------------------------------------------
typedef enum _TSI_OP_MODE 
{
   TSI_OP_MODE_NORMAL,      // Set the camera's operating mode to "normal" (Default)
   TSI_OP_MODE_PDX,         // Set the camera's operating mode to "PDX"
   TSI_OP_MODE_TOE,         // Set the camera's operating mode to "TOE"
   TSI_OP_MODE_RESERVED_1,  // Reserved
   TSI_MAX_OP_MODES

} TSI_OP_MODE, *PTSI_OP_MODE;

//------------------------------------------------------------------------------
// String Sizes
//------------------------------------------------------------------------------
#define TSI_MAX_CAM_NAME_LEN		64

//------------------------------------------------------------------------------
// Enumerations
//------------------------------------------------------------------------------
typedef enum _TSI_EXPOSURE_UNITS 
{
   TSI_EXP_UNIT_MICROSECONDS,
   TSI_EXP_UNIT_MILLISECONDS,
   TSI_EXP_UNIT_MAX

} TSI_EXPOSURE_UNITS, *PTSI_EXPOSURE_UNITS;



//------------------------------------------------------------------------------
// TSI_BOOL
//------------------------------------------------------------------------------
typedef enum _TSI_BOOL 
{
   TSI_FALSE   = 0,
   TSI_TRUE    = 1,
   TSI_DISABLE = TSI_FALSE,
   TSI_ENABLE  = TSI_TRUE

} TSI_BOOL, *PTSI_BOOL;





//------------------------------------------------------------------------------
// Forward declarations.
//------------------------------------------------------------------------------
class TsiImage;
class TsiImageUtil;



//------------------------------------------------------------------------------
// Callback function data.
//------------------------------------------------------------------------------
typedef struct _TSI_FUNCTION_CAMERA_CONTROL_INFO 
{
   uint32_t FrameNumber;

   struct 
   {
     uint32_t Year;
     uint32_t Month;
     uint32_t Day;
     uint32_t Hour;
     uint32_t Min;
     uint32_t Sec;
     uint32_t MS;
     uint32_t US;

   } TimeStamp;

} TSI_FUNCTION_CAMERA_CONTROL_INFO, *PTSI_FUNCTION_CAMERA_CONTROL_INFO;


//------------------------------------------------------------------------------
// Callback function prototypes.
//------------------------------------------------------------------------------
//
// TSI_CALLBACK_CAMERA_CONTROL_FUNCTION     - This callback function will only
//                                            receive camera control events.
//
// TSI_CALLBACK_CAMERA_CONTROL_FUNCTION_EX  - Same as above, but adds timestamp and frame
//                                            number for events.  **Warning, ctl_event_info
//                                            is only valid for the duration of the callback.
//
// TSI_FUNCTION_IMAGE_NOTIFICATION_CALLBACK - This callback function is invoked when
//                                            there is frame data available.  The caller must
//                                            issue a separate call to retrieve the image data.
//
// TSI_FUNCTION_IMAGE_CALLBACK              - This callback function is invoked when 
//                                            there is frame data available.  The image data is
//                                            passed to the callback function for immediate 
//                                            processing.  **Warning, this callback must not be
//                                            used in conjuction with the GetPendingImage,
//                                            GetLastPendingImage, or FreeImage methods.
//
//------------------------------------------------------------------------------
typedef void (__cdecl *TSI_FUNCTION_CAMERA_CONTROL_CALLBACK    ) (int  ctl_event,      void *context);
typedef void (__cdecl *TSI_FUNCTION_CAMERA_CONTROL_CALLBACK_EX ) (int  ctl_event,      TSI_FUNCTION_CAMERA_CONTROL_INFO *ctl_event_info, void *context);
typedef void (__cdecl *TSI_FUNCTION_IMAGE_NOTIFICATION_CALLBACK) (int  notification,   void *context);
typedef void (__cdecl *TSI_FUNCTION_IMAGE_CALLBACK             ) (TsiImage *tsi_image, void *context);
typedef void (__cdecl *TSI_TEXT_CALLBACK_FUNCTION              ) (char     *str,           void *context);


//==============================================================================
// TsiCamera C++ Class
//------------------------------------------------------------------------------
//==============================================================================
class TsiCamera
{
   //---------------------------------------------------------------------------
   // PUBLIC
   //---------------------------------------------------------------------------
   public:

      virtual bool            Open                 (void            );
      virtual bool            Close                (void            );

      virtual bool            Status               (TSI_CAMERA_STATUS *status);

      virtual char           *GetCameraName        (void            );
      virtual bool            SetCameraName        (char *name      );

      virtual int             GetDataTypeSize      (TSI_DATA_TYPE    data_type);

      virtual int             GetParameter         (TSI_PARAM_ID param_id );
      virtual bool            GetParameter         (TSI_PARAM_ID param_id, size_t length, void *data);

      virtual bool            SetParameter         (TSI_PARAM_ID param_id, void  *data  );
      virtual bool            SetParameter         (TSI_PARAM_ID param_id, int    value );

      virtual bool            ResetCamera          (void             );

      virtual TsiImage       *GetPendingImage      (void             );
      virtual TsiImage       *GetLastPendingImage  (void             );
      virtual bool            FreeAllPendingImages (void             ); 
      virtual bool            FreeImage            (TsiImage        *);       

      virtual bool            StartAndWait         (int timeout_ms   );
      virtual bool            Start                (void             );
      virtual bool            Stop                 (void             );

      virtual int             GetAcquisitionStatus (void             );
      virtual int             GetExposeCount       (void             );
      virtual int             GetFrameCount        (void             );
      virtual bool            WaitForImage         (int timeout_ms = TSI_WAIT_INFINITE);
      virtual bool            ResetExposure        (void             );

      virtual char           *GetLastErrorStr      (void                                       );
      virtual TSI_ERROR_CODE  GetErrorCode         (void                                       );
      virtual bool            ClearError           (void                                       );
      virtual bool            GetErrorStr          (TSI_ERROR_CODE code, char *str, int &str_len);

      virtual bool            SetTextCommand               (char *str                                );
      virtual bool            SetTextCallback              (TSI_TEXT_CALLBACK_FUNCTION, void *context);

      virtual bool            SetCameraControlCallback     (TSI_FUNCTION_CAMERA_CONTROL_CALLBACK     func, void *context);
      virtual bool            SetCameraControlCallbackEx   (TSI_FUNCTION_CAMERA_CONTROL_CALLBACK_EX  func, void *context);
      virtual bool            SetImageNotificationCallback (TSI_FUNCTION_IMAGE_NOTIFICATION_CALLBACK func, void *context);
      virtual bool            SetImageCallback             (TSI_FUNCTION_IMAGE_CALLBACK              func, void *context);


      //------------------------------------------------------------------------
      // Trigger based image acquisition.
      //------------------------------------------------------------------------
      virtual bool            StartTriggerAcquisition  (void);
      virtual bool            StopTriggerAcquisition   (bool rearm);
      virtual bool            SWTrigger                (void);

      
   //---------------------------------------------------------------------------
   // PROTECTED
   //---------------------------------------------------------------------------
   protected:
               TsiCamera (void);
      virtual ~TsiCamera (void);
};

#endif
