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


/* All MCS commands return a status/error code which helps analyzing 
   problems */
void ExitIfError(SA_STATUS st) {
    if(st != SA_OK) {
        printf("MCS error %u\n",st);
        exit(1);
    }
}

int main(int argc, char* argv[])
{
    unsigned int idList[16];
    unsigned int idListSize = 16;
    unsigned int sensorEnabled = 0;

    /* Get a list of all MCS devices available on this computer. The list
       contains MCS IDs which are unique numbers to identify a MCS. */

    ExitIfError( SA_GetAvailableSystems(idList,&idListSize) );
    if(idListSize == 0)
    {
        printf("No MCS found\n");
        return 1;
    }
    printf("%u MCS are currently connected\n",idListSize);

    /* Select one MCS ID to initialize only this device. Add the ID to the 
       init-list. If more than one device should be initialized, add all 
       their IDs to the list. If the list is empty the following InitSystems
       command it will initialize all available MCS. */

    ExitIfError( SA_ClearInitSystemsList() ) ;
    ExitIfError( SA_AddSystemToInitSystemsList(idList[0]) ) ;


    /* When initializing the controller(s) you must select one of the two 
       communication modes:
    synchronous: only commands from the set of synchronous commands can 
        be used in the program. In sync. communication mode commands like
        GetPosition, GetStatus etc. return the requested value directly. 
        this is easier to program, especially for beginners.
    asyncronous: only asynchronous commands can be used. In this mode Get... 
        commands send a request message to the MCS controller but do not 
        wait for the reply. The replied message must be catched with special
        commands ReceiveNextPacket, ReceiveNextPacketIfChannel or 
        LookAtNextPacket, which are only available in async. communication
        mode. Please read the MCS Programmer's Guide for more information. */

    ExitIfError( SA_InitSystems(SA_SYNCHRONOUS_COMMUNICATION) );

    /* Now the MCS is initialized and can be used.
       In this demo program all we do is reading the sensor power-mode. */

    ExitIfError( SA_GetSensorEnabled_S(0,&sensorEnabled) );
    switch(sensorEnabled)
    {
    case SA_SENSOR_DISABLED: printf("Sensors are disabled\n"); break;
    case SA_SENSOR_ENABLED: printf("Sensors are enabled\n"); break;
    case SA_SENSOR_POWERSAVE: printf("Sensors are in power-save mode\n"); break;
    default: printf("Error: unknown sensor power status\n"); break;
    }

    /* At the end of the program you should release all initialized systems. */

    ExitIfError( SA_ReleaseSystems() );

    return 0;
}