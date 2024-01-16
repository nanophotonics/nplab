#include "DFRobot_MCP4725.h"
#include "string.h"
#define  REF_VOLTAGE    5000
DFRobot_MCP4725 DAC;

  // temporary array for use when parsing

const byte numChars = 32;
char receivedChars[numChars];
char tempChars[numChars];        
bool is_value_command=false;
      // variables to hold the parsed data
char messageFromPC[numChars] = {0};
float floatFromPC = 0.0;
boolean newData = false;




// defining variables for operation

uint16_t step_size = 10; // 10mV
uint16_t ulim = 5000; // 5V
uint16_t llim = 0; //0 V
float Vin = 0;
float Vout = 1500;
int target_voltage = 400; // in port values
bool is_locking = false;
bool is_target_value=false;
float voltage_step=3;
float input_tolerance=2;
int lock_time=1000;




void setup(void) {

  Serial.begin(9600);
  /* MCP4725A0_address is 0x60 or 0x61
   * MCP4725A0_IIC_Address0 -->0x60
   * MCP4725A0_IIC_Address1 -->0x61
   */
  DAC.init(MCP4725A0_IIC_Address0, REF_VOLTAGE);
  //Serial.println("This demo expects 1/2 pieces of data - text, and and integer");
  //Serial.println("Enter data in this style <command:value>  ");
  //Serial.println();
  set_Vout(Vout);

}

//======================================================================

//                           MAIN PROGRAM

//=======================================================================

void loop() {
    recvWithStartEndMarkers();
    if (newData == true) {
        strcpy(tempChars, receivedChars);
        is_value_command = search_char(tempChars,':');
//        if (is_value_command==true) {
//          Serial.println("true");
//        }
//        else {
//          Serial.println("false");
//        }
            // this temporary copy is necessary to protect the original data
            //   because strtok() used in parseData() replaces the commas with \0
        parseData();
        // showParsedData();
        newData = false;
        commandAction();
    }
    locking_action(); // performs locking action if locking is on

}

//=============================================================================================

//                 INPUT DETECTION COMMANDS

//=============================================================================================

bool search_char(char * char_array,char C){
  // search for C in char_array, return true if exists and false if not
  int ii=0;
  while (char_array[ii]!='\0'){
    //Serial.print(ii);
    if (char_array[ii]==C) {
      return true;
    }
    ii++;
  }
  return false;
}


// function reads input between < > markers

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;

    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

//============

void parseData() {      // split the data into its parts

    char * strtokIndx; // this is used by strtok() as an index

    strtokIndx = strtok(tempChars,":");      // get the first part - the string
    strcpy(messageFromPC, strtokIndx); // copy it to messageFromPC
    if (is_value_command==true) {
        strtokIndx = strtok(NULL, ":");
        floatFromPC = atof(strtokIndx);     // convert this part to a float
    }
    else {floatFromPC = -1;}
}

//============

void showParsedData() {
    //Serial.print("Message ");
    Serial.println(messageFromPC);
    if (is_value_command==true) {
        //Serial.print("Float ");
        Serial.println(floatFromPC);
    }
}


//=========================================================================================

//                          OPERATION COMMANDS

//=========================================================================================
void get_Vin(){  //(bool show=false){
  long sum = 0;
  int iters = 1000;
  for (int i = 0; i <= iters; i++) {
    int sensorValue = analogRead(A0);
    sum = sum+sensorValue;
  }
  long Vin = sum/iters;
//      if (show==true) {
//          Serial.println(Vin);
//      }
  Serial.println(Vin);

}

//====================================

void set_target(){
  get_Vin();
  target_voltage=Vin;
}
//=======================================
void get_target() {
  Serial.println(target_voltage);
}

//=======================================

void set_Vout(float input_number){
  Vout=input_number;
  DAC.outputVoltage(Vout);
}
  
//=================

void get_Vout(){
  Serial.println(Vout);
}

//=============

void is_locked(){
  if (is_locking) {
    Serial.println("True");
  }
  else {
    Serial.println("False");
  }
}

//============

void start_locking(){
  is_locking=true;
}
//  ============================
// locking action 
//=============================

void locking_action() {
  if (is_locking==true) {
    get_Vin();
    //=================================
    // for up-slope: decrease output if input is above target; 
    // increase output if input is below target
    
//    if (Vin > target_voltage+input_tolerance) {
//      float new_Vout=Vout-voltage_step;
//      if (new_Vout>llim) {
//        set_Vout(new_Vout);
//      }
//    }
//    if (Vin < target_voltage-input_tolerance) {
//      float new_Vout = Vout+voltage_step;
//      if (new_Vout<ulim) {
//        set_Vout(new_Vout);
//      }
//    }
    
    //=====================================
    // for down-slope: increase output if input is above target;
    // decrease output if input is below target

    if (Vin > target_voltage+input_tolerance) {
      float new_Vout=Vout+voltage_step;
      if (new_Vout<ulim) {
        set_Vout(new_Vout);
      }
    }
    if (Vin < target_voltage-input_tolerance) {
      float new_Vout = Vout-voltage_step;
      if (new_Vout>llim) {
        set_Vout(new_Vout);
      }
    }

    //========================================
    //delay(lock_time);
  }
  
}



//============
void stop_locking(){
  is_locking = false;
}

//=================================================
void set_step(){
  voltage_step=int(floatFromPC);
}
//===============================================
void get_step(){
  Serial.println(voltage_step);
}
//================================================

void set_tolerance(){
  input_tolerance=int(floatFromPC);
}
//===============================================
void get_tolerance(){
  Serial.println(input_tolerance);
}
//=================================================


void commandAction(){
// GVI:get_Vin(); ST:set_target(); SVO:set_Vout();GVO:get_Vout;  IL:is_locked; SL:start_locking();QL:quit_locking;SS:set_step;GS:get_step
// GT:get_target; SIT: set_input_tolerance; GIT: get_input_tolerance; 
  //Serial.println("starting command action");
  if (strcmp(messageFromPC,"GVI") == 0) {
    //Serial.println("identified command GVI");
    //get_Vin(true);
    get_Vin();
  }
  if (strcmp(messageFromPC,"ST") == 0) {
    set_target();
  }
  if (strcmp(messageFromPC,"SVO") == 0) {
    set_Vout(floatFromPC); 
  }
  if (strcmp(messageFromPC,"GVO") == 0) {
    get_Vout();
  }
  if (strcmp(messageFromPC,"IL") == 0) {
    //Serial.println("identified command IL");
    is_locked();
  }
  if (strcmp(messageFromPC,"SL") == 0) {
    start_locking();
  }
  if (strcmp(messageFromPC,"QL") == 0) {
    stop_locking();
  }
  if (strcmp(messageFromPC,"SS") == 0) {
    set_step();
  }
  if (strcmp(messageFromPC,"GS") == 0) {
    get_step();
  }
  if (strcmp(messageFromPC,"GT") == 0) {
    get_target();
  }
  if (strcmp(messageFromPC,"GIT") == 0) {
    get_tolerance();
  }
  if (strcmp(messageFromPC,"SIT") == 0) {
    set_tolerance();
  }
}
