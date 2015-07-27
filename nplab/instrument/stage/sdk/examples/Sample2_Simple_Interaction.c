/**********************************************************************
* Copyright (c) 2013 SmarAct GmbH
*
* This is a programming example for the Modular Control System API.
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
#include <stdio.h>
#include <MCSControl.h>


int main(int argc, char* argv[])
{
    SA_STATUS error = SA_OK;
    unsigned int sys = 0;
    unsigned int numOfChannels = 0;
    unsigned int channel = 0;
    unsigned int sensorType;
    int linearSensorPresent = 0;
    int key;
    unsigned int status;
    int position;

    // ----------------------------------------------------------------------------------
    // init systems
    error = SA_InitSystems(SA_SYNCHRONOUS_COMMUNICATION);			
    printf("Init systems: Error: %u\n", error);
    if(error)
        return 1;

    error = SA_GetNumberOfChannels(sys,&numOfChannels);
    printf("Number of Channels: %u\n",numOfChannels);


    // ----------------------------------------------------------------------------------
    // check availability of linear sensor
    error = SA_GetSensorType_S(sys, channel, &sensorType);												
    if (sensorType == SA_S_SENSOR_TYPE ||
        sensorType == SA_M_SENSOR_TYPE ||
        sensorType == SA_SC_SENSOR_TYPE ||
        sensorType == SA_SP_SENSOR_TYPE) {
            linearSensorPresent = 1;
            printf("Linear sensor present\n");
        } else {
            linearSensorPresent = 0;
            printf("No linear sensor present\n");
        }
    // ----------------------------------------------------------------------------------
    printf("\nENTER COMMAND AND RETURN\n"
            "+  Move positioner up by 100um\n"
            "-  Move positioner down by 100um\n"
            "q  Quit program\n");

    // ----------------------------------------------------------------------------------
    do
    {
        key = getchar();
        if (key == '-')											
            if (linearSensorPresent)							
                SA_GotoPositionRelative_S(sys, channel, -100000, 1000);	
            else
                SA_StepMove_S(sys, channel,-200, 4095, 10000);							

        if (key == '+')											
            if (linearSensorPresent)							
                SA_GotoPositionRelative_S(sys, channel, 100000, 1000);	
            else
                SA_StepMove_S(sys, channel, 200, 4095, 10000);							

        // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        // wait until movement has finished
        do {
            SA_GetStatus_S(sys, channel, &status);	
            Sleep(50);
        } while (status == SA_TARGET_STATUS);

        // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
        if (linearSensorPresent) {
            SA_GetPosition_S(sys, channel, &position);
            printf("Position: %d nm\n", position);
        }
        // - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    } while (key != 'q');

    error = SA_ReleaseSystems();
    printf("Release systems: Error: %u\n", error);

    return 0;
}