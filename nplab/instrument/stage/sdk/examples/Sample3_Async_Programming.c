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


void PrintMcsError(SA_STATUS st) {
    printf("MCS error %u\n",st);
}

/* All MCS commands return a status/error code which helps analyzing 
   problems */
void ExitIfError(SA_STATUS st) {
    if(st != SA_OK) {
        PrintMcsError(st);
        exit(1);
    }
}



int main(int argc, char* argv[])
{
    unsigned int numOfChannels = 0;
    SA_INDEX channelA = 0, channelB = 1;
    int stop = 0;
    int chanAStopped = 0, chanBStopped = 0;
    SA_PACKET packet;

    ExitIfError( SA_InitSystems(SA_ASYNCHRONOUS_COMMUNICATION) );		

    ExitIfError( SA_GetNumberOfChannels(0,&numOfChannels) );
    printf("Number of Channels: %u\n",numOfChannels);

    /* If buffered output is enabled the commands are collected in a 
       buffer on the PC-side. To send the buffer to the MCS FlushOutput
       is used. Buffering is useful to prepare some commands (e.g. 
       movements) and send them to the MCS simultaneously. */

    ExitIfError( SA_SetBufferedOutput_A(0,SA_BUFFERED_OUTPUT) );

    /* This stores movement commands for two positioners in the buffer.
       FlushOutput sends them to the MCS so both positioners will start 
       moving (almost) simultaneously. */

    ExitIfError( SA_StepMove_A(0,channelA,3000,4000,800) );
    ExitIfError( SA_StepMove_A(0,channelB,2000,4000,1000) );
    ExitIfError( SA_FlushOutput_A(0) );

    /* now poll the status of the two channels until both have 'stopped' status */

    while(!stop)
    {
        SA_GetStatus_A(0,channelA);
        SA_GetStatus_A(0,channelB);
        ExitIfError( SA_FlushOutput_A(0) );

        /* To receive data from the MCS store the Get... commands in the
           buffer and flush it. 
           Receive two packets from the MCS. The code should be prepared to handle
           unexpected packets like error packets beside the expected ones 
           (here: status packets). Also remember that ReceiveNextPacket could 
           timeout before a packet is received, which is indicated by a 
           SA_NO_PACKET_TYPE packet. */

        ExitIfError( SA_ReceiveNextPacket_A(0,1000,&packet) );
        switch(packet.packetType)
        {
        case SA_NO_PACKET_TYPE:
            break;
        case SA_ERROR_PACKET_TYPE:
            PrintMcsError(packet.data1);
            stop = 1;
            break;
        case SA_STATUS_PACKET_TYPE:
            if(packet.channelIndex == channelA)
                chanAStopped = (packet.data1 == SA_STOPPED_STATUS);
            else if(packet.channelIndex == channelB)
                chanBStopped = (packet.data1 == SA_STOPPED_STATUS);
            stop = (chanAStopped && chanBStopped);
            break;
        }
    }

    ExitIfError( SA_ReleaseSystems() );

    return 0;
}