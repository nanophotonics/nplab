/**********************************************************************
* Copyright (c) 2013 SmarAct GmbH
*
* This sample program shows how to work with channel properties.
* (please read the MCS Programmer's Guide chapter about channel
* properties first)
* Properties are key/value pairs in the MCS that affect the behavior
* of the controller. To read or write the value of a property, the
* property must be addressed with its key. Keys consist of a component
* selector, a sub-component selector and the property name.
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
    SA_STATUS error = SA_OK;
    int value;

    ExitIfError( SA_InitSystems(SA_SYNCHRONOUS_COMMUNICATION) );	

    /* Read the value of the low-vibration operation mode property which
       is 1 if the low-vibration movement mode is active. 
       The utilitiy function SA_EPK (encode property key) converts the
       three components of a property key to an unsigned int which is
       passed to the property get and set functions. */

    ExitIfError( SA_GetChannelProperty_S(0,0,
                    SA_EPK(SA_GENERAL,SA_LOW_VIBRATION,SA_OPERATION_MODE),&value) );
    printf("Low-Vibration operation mode property is %i\n",value);

    /* This reads another property (the current value of the internal counter #0). 
       The sub-component here is an integer number which is the index of the
       counter. 
       Note: when reading a property in asynchronous mode the value is returned
       in a CHANNEL_PROPERTY_PACKET */

    ExitIfError( SA_GetChannelProperty_S(0,0,
                    SA_EPK(SA_COUNTER,0,SA_VALUE),&value) );
    printf("Counter 0 value is %i\n",value);

    /* Reset counter #0 by setting its value to 0 */

    printf("Resetting counter 0\n");
    ExitIfError( SA_SetChannelProperty_S(0,0,
                    SA_EPK(SA_COUNTER,0,SA_VALUE),42) );

    ExitIfError( SA_ReleaseSystems() );

    return 0;
}