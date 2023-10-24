/*	Monochrome Polling Example
*
*	Goes through each step to open up the SDKs for a Thorlabs compact-scientific camera, sets the
*	exposure to 10ms, waits for 10 images, then closes the camera and SDKs. This method uses
*	Polling Mode to acquire frames from the camera instead of using frame-available callbacks.
*	This reduces code complexity, but there is a chance to miss frames, especially if poll rate is slower
*	than frame rate.
*
*	By default, this example is going to perform software triggering. There are comments explaining
*	how to edit the example to use hardware triggering.
*
*	Include the following files in your application to utilize the camera sdk:
*		tl_camera_sdk.h
*		tl_camera_sdk_load.h
*		tl_camera_sdk_load.c
*
*	This example produces monochrome images.
*/


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tl_camera_sdk.h"
#include "tl_camera_sdk_load.h"

int is_camera_sdk_open = 0;
int is_camera_dll_open = 0;
void *camera_handle = 0;

int report_error_and_cleanup_resources(const char *error_string);
int initialize_camera_resources();

int main(void)
{
    if (initialize_camera_resources())
        return 1;

    // Set the exposure
    long long const exposure = 10000; // 10 ms
    if (tl_camera_set_exposure_time(camera_handle, exposure))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    printf("Camera exposure set to %lld\n", exposure);

    // Set the gain
    int gain_min;
    int gain_max;
    if (tl_camera_get_gain_range(camera_handle, &gain_min, &gain_max))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    if(gain_max > 0)
    {
        // this camera supports gain, set it to 6.0 decibels
        const double gain_dB = 6.0;
        int gain_index;
        if (tl_camera_convert_decibels_to_gain(camera_handle, gain_dB, &gain_index))
            return report_error_and_cleanup_resources(tl_camera_get_last_error());
        tl_camera_set_gain(camera_handle, gain_index);
    }


    // Configure camera for continuous acquisition by setting the number of frames to 0.
    if (tl_camera_set_frames_per_trigger_zero_for_unlimited(camera_handle, 0))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());

    // Set camera to wait 100 ms for a frame to arrive during a poll.
    // If an image is not received in 100ms, the returned frame will be null
    if (tl_camera_set_image_poll_timeout(camera_handle, 100))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());

    /**HARDWARE TRIGGER**/
    /*
        The alternative to software triggering. This is specified by tl_camera_set_operation_mode().
        By default, the operation mode is TL_CAMERA_OPERATION_MODE_SOFTWARE_TRIGGERED, which means that
        the camera will not be listening for hardware triggers.
        TL_CAMERA_OPERATION_MODE_HARDWARE_TRIGGERED means for each hardware trigger the camera will take an image
        with exposure equal to the current value of tl_camera_get_exposure_time_us().
        TL_CAMERA_OPERATION_MODE_BULB means that exposure will be equal to the duration of the high pulse (or low, depending on polarity).

        Uncomment the next two blocks of code to set the trigger polarity and set the camera operation mode to Hardware Triggered mode.
    */
    //// Set the trigger polarity for hardware triggers (ACTIVE_HIGH or ACTIVE_LOW)
    //if (tl_camera_set_trigger_polarity(camera_handle, TL_CAMERA_TRIGGER_POLARITY_ACTIVE_HIGH))
    //	return report_error_and_cleanup_resources(tl_camera_get_last_error());

    //// Set trigger mode
    //if (tl_camera_set_operation_mode(camera_handle, TL_CAMERA_OPERATION_MODE_HARDWARE_TRIGGERED))
    //	return report_error_and_cleanup_resources(tl_camera_get_last_error());
    //printf("Hardware trigger mode activated\n");

    // Arm the camera.
    // if Hardware Triggering, make sure to set the operation mode before arming the camera.
    if (tl_camera_arm(camera_handle, 2))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    printf("Camera armed\n");

    /**SOFTWARE TRIGGER**/
    /*
        Once the camera is initialized and armed, this function sends a trigger command to the camera over USB, GE, or CL.
        Pending images can be acquired using tl_camera_get_pending_frame_or_null().
        Continuous acquisition is specified by setting the number of frames to 0 and issuing a single software trigger request.

        Comment out the following code block if using Hardware Triggering.
    */
    if (tl_camera_issue_software_trigger(camera_handle))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    printf("Software trigger sent\n");


    //initialize frame variables
    unsigned short *image_buffer = 0;
    int frame_count = 0;
    unsigned char *metadata = 0;
    int metadata_size_in_bytes = 0;

    //Poll for 10 images
    int count = 0;

    while (count < 10)
    {
        if (tl_camera_get_pending_frame_or_null(camera_handle, &image_buffer, &frame_count, &metadata, &metadata_size_in_bytes))
            return report_error_and_cleanup_resources(tl_camera_get_last_error());
        if (!image_buffer)
            continue; //timeout

        printf("Pointer to image: 0x%p\n", image_buffer);
        printf("Frame count: %d\n", frame_count);
        printf("Pointer to metadata: 0x%p\n", metadata);
        printf("Metadata size in bytes: %d\n", metadata_size_in_bytes);

        count++;
    }

    printf("Images received! Closing camera...\n");

    // Stop the camera.
    if (tl_camera_disarm(camera_handle))
        printf("Failed to stop the camera!\n");

    // Clean up and exit
    return report_error_and_cleanup_resources(0);
}

/*
    Initializes camera sdk and opens the first available camera. Returns a nonzero value to indicate failure.
 */
int initialize_camera_resources()
{
    // Initializes camera dll
    if (tl_camera_sdk_dll_initialize())
        return report_error_and_cleanup_resources("Failed to initialize dll!\n");
    printf("Successfully initialized dll\n");
    is_camera_dll_open = 1;

    // Open the camera SDK
    if (tl_camera_open_sdk())
        return report_error_and_cleanup_resources("Failed to open SDK!\n");
    printf("Successfully opened SDK\n");
    is_camera_sdk_open = 1;

    char camera_ids[1024];
    camera_ids[0] = 0;

    // Discover cameras.
    if (tl_camera_discover_available_cameras(camera_ids, 1024))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    printf("camera IDs: %s\n", camera_ids);

    // Check for no cameras.
    if (!strlen(camera_ids))
        return report_error_and_cleanup_resources("Did not find any cameras!\n");

    // Camera IDs are separated by spaces.
    char* p_space = strchr(camera_ids, ' ');
    if (p_space)
        *p_space = '\0'; // isolate the first detected camera
    char first_camera[256];

    // Copy the ID of the first camera to separate buffer (for clarity)
#ifdef _WIN32
    strcpy_s(first_camera, 256, camera_ids);
#elif defined __linux__
    strcpy(first_camera, camera_ids);
#endif
    printf("First camera_id = %s\n", first_camera);

    // Connect to the camera (get a handle to it).
    if (tl_camera_open_camera(first_camera, &camera_handle))
        return report_error_and_cleanup_resources(tl_camera_get_last_error());
    printf("Camera handle = 0x%p\n", camera_handle);

    return 0;
}

/*
    Reports the given error string if it is not null and closes any opened resources. Returns the number of errors that occured during cleanup, +1 if error string was not null.
 */
int report_error_and_cleanup_resources(const char *error_string)
{
    int num_errors = 0;

    if (error_string)
    {
        printf("Error: %s\n", error_string);
        num_errors++;
    }

    printf("Closing all resources...\n");

    if (camera_handle)
    {
        if (tl_camera_close_camera(camera_handle))
        {
            printf("Failed to close camera!\n%s\n", tl_camera_get_last_error());
            num_errors++;
        }
        camera_handle = 0;
    }
    if (is_camera_sdk_open)
    {
        if (tl_camera_close_sdk())
        {
            printf("Failed to close SDK!\n");
            num_errors++;
        }
        is_camera_sdk_open = 0;
    }
    if (is_camera_dll_open)
    {
        if (tl_camera_sdk_dll_terminate())
        {
            printf("Failed to close dll!\n");
            num_errors++;
        }
        is_camera_dll_open = 0;
    }

    printf("Closing resources finished.\n");
    return num_errors;
}
