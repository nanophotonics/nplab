/******************************************************************************/
/* TSI_ERROR.H                                                                */
/*----------------------------------------------------------------------------*/
/* Copywrite, etc, blah blah blah                                             */
/******************************************************************************/
#ifndef __THORLABS_SCIENTIFIC_IMAGING_ERROR_H__
#define __THORLABS_SCIENTIFIC_IMAGING_ERROR_H__

//------------------------------------------------------------------------------
// Error codes that can be returned from TSI API calls
//------------------------------------------------------------------------------

typedef enum _TSI_ERROR_CODE {

	TSI_NO_ERROR,
	TSI_ERROR_UNKNOWN,

	TSI_ERROR_UNSUPPORTED,

	TSI_ERROR_PARAMETER_UNSUPPORTED,
	TSI_ERROR_ATTRIBUTE_UNSUPPORTED,

	TSI_ERROR_INVALID_ROI,
	TSI_ERROR_INVALID_BINNING,

	TSI_ERROR_INVALID_PARAMETER,
	TSI_ERROR_INVALID_PARAMETER_SIZE,

	TSI_ERROR_PARAMETER_UNDERFLOW,
	TSI_ERROR_PARAMETER_OVERFLOW,

	TSI_ERROR_CAMERA_COMM_FAILURE,

	TSI_ERROR_CAMERA_INVALID_DATA,

	TSI_ERROR_NULL_POINTER_SUPPLIED,
	TSI_ERROR_CAMERA_INVALID_DATA_SIZE_OR_TYPE,
   TSI_ERROR_IMAGE_BUFFER_OVERFLOW,

   TSI_ERROR_INVALID_NUMBER_OF_IMAGE_BUFFERS,
   TSI_ERROR_IMAGE_BUFFER_ALLOCATION_FAILURE,
   TSI_ERROR_TOO_MANY_IMAGE_BUFFERS,

   TSI_ERROR_INVALID_BINNING_SELECTION,

	TSI_MAX_ERROR

} TSI_ERROR_CODE, *PTSI_ERROR_CODE;

extern const char *TsiErrorName[TSI_MAX_ERROR];

#endif // __THORLABS_SCIENTIFIC_IMAGING_ERROR_H__
