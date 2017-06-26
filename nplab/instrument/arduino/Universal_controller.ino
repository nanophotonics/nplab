String codeVersion( "Version 12 - 31/01/2017 Anthony");
// Example data m,4,100 ( device,motor,filter number steps or wheel turns )

/****** Library *****/
#include <AccelStepper.h>
#include <Wire.h>
#include <Adafruit_MotorShield.h>
#include "utility/Adafruit_PWMServoDriver.h"
#include <Servo.h> 

/****** Stepper setup *****/
Adafruit_MotorShield AFMStop(0x60); // Default address, no jumpers
Adafruit_MotorShield AFMSbot(0x61);

Adafruit_StepperMotor *myStepper1 = AFMStop.getStepper(200, 1);
Adafruit_StepperMotor *myStepper2 = AFMStop.getStepper(200, 2);
Adafruit_StepperMotor *myStepper3 = AFMSbot.getStepper(200, 1);
Adafruit_StepperMotor *myStepper4 = AFMSbot.getStepper(200, 2);

void forwardstep1() {  
  myStepper1->onestep(FORWARD, DOUBLE);
}
void backwardstep1() {  
  myStepper1->onestep(BACKWARD, DOUBLE);
}
AccelStepper stepper1(forwardstep1, backwardstep1);

void forwardstep2() {  
  myStepper2->onestep(FORWARD, DOUBLE);
}
void backwardstep2() {  
  myStepper2->onestep(BACKWARD, DOUBLE);
}
AccelStepper stepper2(forwardstep2, backwardstep2);

void forwardstep3() {  
  myStepper3->onestep(FORWARD, DOUBLE);
}
void backwardstep3() {  
  myStepper3->onestep(BACKWARD, DOUBLE);
}
AccelStepper stepper3(forwardstep3, backwardstep3);

void forwardstep4() {  
  myStepper4->onestep(FORWARD, DOUBLE);
}
void backwardstep4() {  
  myStepper4->onestep(BACKWARD, DOUBLE);
}
AccelStepper stepper4(forwardstep4, backwardstep4);

/******** Filterwheel constants **********/
int hallPin = 1;
int hallState = 0;

// Fiter positions in steps from zero
int filterposition[7]={0,87,242,397,552,607,762};

/******** Mirror mount constants **********/
// Ratio to turn the wheel one turn approx at double setting
 int ratio = 11000;

/******** Servo setup **********/
Servo myservo1;  // create servo object to control a servo 
Servo myservo2;  // create servo object to control a servo 
int pos = 0;    // variable to store the servo position
int positionPin1 = 1; // Analog input
int positionPin2 = 2;

/******** Data input setup **********/
int dataAnalog = 3; // Analog input
int dataDigital = 8; // Digital input with 10k resistor

/******** Other default constants ********/
int stepper = 0;
String steps ;
int selection = 0;
float amount = 0;

/********** Error setup **********/
int itemError = 0; // no errors

/******** Setup *********/
void setup(){
  Serial.begin(9600);
    Serial.println(codeVersion);
    Serial.println();
    Serial.println("*** You have to wait for one movement to complete before sending another command");
    Serial.println(" - serial is also blocked ***");
    Serial.println("d = Data socket - d,1,1 Digital input has a 10k pull up resistor");
    Serial.println("f = Filter wheel - filter number");
    Serial.println("m = Mirror mount - Worm wheel rotations");
    Serial.println("s = Servo - angle");
    Serial.println("o = Stepper direct - steps");
    Serial.println("Input command in the format m,2,500");
    Serial.println("device,stepper,filter steps or or wheel turns");
    Serial.println("Any analog data will be random unless there is a device connected to the pin");
    Serial.println();
  AFMStop.begin(); 
  AFMSbot.begin();
  // Below did not seem to make any difference
  //TWBR = ((F_CPU /400000l) - 16) / 2; // Change the i2c clock to 400KHz
  int maxSpeed = 255;
  int maxAcceleration = 100.0;
  stepper1.setMaxSpeed(maxSpeed);
  stepper1.setAcceleration(maxAcceleration);
  stepper2.setMaxSpeed(maxSpeed);
  stepper2.setAcceleration(maxAcceleration); 
  stepper3.setMaxSpeed(maxSpeed);
  stepper3.setAcceleration(maxAcceleration);
  stepper4.setMaxSpeed(maxSpeed);
  stepper4.setAcceleration(maxAcceleration);
  myservo1.attach(9);
  myservo2.attach(10);
}

void loop(){    
    while (Serial.available()==0)  {       
        String split = Serial.readString();
        String item = getValue(split, ',', 0);
        String motor = getValue(split, ',', 1);
        String steps = getValue(split, ',', 2);

        // Convert selection to integer
        selection = motor.toInt();       
        // Convert steps to float   
        char carray[steps.length() + 1]; //determine size of the array
        steps.toCharArray(carray, sizeof(carray)); //put readStringinto an array
        float amount = atof(carray); //convert the array into a float  
        
// Setup variables depending on the motor being used
    switch (selection) {
      case 0:
      {
        itemError = 0;
      }
      break; 
      case 1:
      {
        stepper = 1;
        hallPin = 5;
        itemError = 0;
      }
      break;
      case 2:
      {
        stepper = 2;
        hallPin = 4;
        itemError = 0;
      }
      break;
      case 3:
      {
        stepper = 3;
        hallPin = 3;
        itemError = 0;
      }
      break;
      case 4:
      {
        stepper = 4;
        hallPin = 2;
        itemError = 0;
      }
      break;  
      default:
      {
       Serial.println(selection);
       if ( itemError == 0 ){
          Serial.println();
          Serial.println("Incorrect motor data should be in the range of 1-4");
          itemError = 1;
       }
        stepper = 0;
      }
        break;      
                     }
                         
      // Data socket
      if (item == "d"){
       Serial.print("Analog data = ");
       Serial.println(analogRead(dataAnalog));
       Serial.print("Digital data = ");
       Serial.println(digitalRead(dataDigital));
      }   
      
    // Filter wheel code
    if (item == "f" )
    {   
      if (amount == 0) {
        zero(hallPin,stepper);
      }    
      else if (amount == 1) {
        nextFilter(filterposition[1],amount,stepper);
      }        
      else if (amount == 2) {
        nextFilter(filterposition[2],amount,stepper);
      }       
      else if (amount == 3) {
        nextFilter(filterposition[3],amount,stepper);
      }      
      else if (amount == 4) {
        nextFilter(filterposition[4],amount,stepper);
      }       
      else if (amount == 5) {
        nextFilter(filterposition[5],amount,stepper);
      }     
      else if (amount == 6) {
        nextFilter(filterposition[6],amount,stepper);
      }
    else {Serial.println("Filter numbers between 1 & 6 with 0 to zero the wheel");} 
                        }
                        
    // mount or other section
    else if ((item == "m" )||(item == "o" ))
     { 
        if (item == "m"){     
        // Calculation to turn value sent from PC into steps e.g deg to step
        // 10 Double turns = 0.182deg
        // Set the variable in the setup section e.g. rotation = 400 and use that below
        amount = amount * ratio;
                        }      
   if (stepper == 1){
        stepper1.move(amount);
        stepper1.runToPosition();
        myStepper1->release();
        Serial.println("Move finished");
                        }
  else if (stepper == 2){
        stepper2.move(amount);
        stepper2.runToPosition();
        myStepper2->release();
        Serial.println("Move finished");
                        }                        
  else if (stepper == 3){
        stepper3.move(amount);
        stepper3.runToPosition();
        myStepper3->release();
        Serial.println("Move finished");
                        }                        
  else if (stepper == 4){; 
        stepper4.move(amount);
        stepper4.runToPosition();
        myStepper4->release();
        Serial.println("Move finished");
                        }
  else {Serial.println("Stepper must be between 1 and 4");}     
  }
     
    // servo section
  else if (item == "s" )
    { 
      if (stepper == 1){
        myservo1.write(amount);
        delay(15); 
        Serial.println();
        Serial.print("Servo 1 angle = ");
        Serial.println(analogRead(positionPin1));
                      } 
     else if (stepper == 2){
       myservo2.write(amount);
       delay(15);
       Serial.println();
       Serial.print("Servo 2 angle = ");
       Serial.println(analogRead(positionPin2));     
                          } 
     else {Serial.println("Servo must be 1 or 2");}                       
    }   
    
  else { 
      /* Serial.print("error="); Serial.println(itemError);
        if ( itemError == 0 ){
          Serial.println();
          Serial.println("There is an error with your equipment selection");
          itemError = 1;
                           }
                           Serial.print("error="); Serial.println(itemError);*/
      }    
      }
}

/******** Filter wheel functions **********/
// Zero wheel function
// Top D4 & D5
// Bottom D2 & D3
void zero(int hallPin, int stepper){
  Serial.println("Homing");
      hallState = digitalRead(hallPin);
if (stepper == 1){
  if (hallState == LOW) {
        stepper1.setCurrentPosition(0);
        stepper1.runToNewPosition(-50);
      }
      hallState = digitalRead(hallPin);
      stepper1.move(934);
      while (hallState == HIGH)
      {      
        stepper1.run();
        hallState = digitalRead(hallPin);
      }
      stepper1.setCurrentPosition(0);
      stepper1.runToNewPosition(5);
      myStepper1->release();
                        }
else if (stepper == 2){
  if (hallState == LOW) {
        stepper2.setCurrentPosition(0);
        stepper2.runToNewPosition(-50);
      }
      hallState = digitalRead(hallPin);
      stepper2.move(934);
      while (hallState == HIGH)
      {      
        stepper2.run();
        hallState = digitalRead(hallPin);
      }
      stepper2.setCurrentPosition(0);
      stepper2.runToNewPosition(5);
      myStepper2->release();
                        }                        
 else if (stepper == 3){
  if (hallState == LOW) {
        stepper3.setCurrentPosition(0);
        stepper3.runToNewPosition(-50);
      }
      hallState = digitalRead(hallPin);
      stepper3.move(934);
      while (hallState == HIGH)
      {      
        stepper3.run();
        hallState = digitalRead(hallPin);
      }
      stepper3.setCurrentPosition(0);
      stepper3.runToNewPosition(5);
      myStepper3->release();
                        }                        
 else if (stepper == 4){
  if (hallState == LOW) {
        stepper4.setCurrentPosition(0);
        stepper4.runToNewPosition(-50);
      }
      hallState = digitalRead(hallPin);
      stepper4.move(934);
      while (hallState == HIGH)
      {      
        stepper4.run();
        hallState = digitalRead(hallPin);
      }
      stepper4.setCurrentPosition(0);
      stepper4.runToNewPosition(5);
      myStepper4->release();
                        }   
      Serial.println("Home");    
}

// Select filter function
void nextFilter(int steps, int number, int stepper){
   if (stepper == 1){
     stepper1.runToNewPosition(steps);
     stepper1.run();
     myStepper1->release();
                        }
  else if (stepper == 2){
    stepper2.runToNewPosition(steps);
    stepper2.run();
    myStepper2->release();
                        }                        
  else if (stepper == 3){
    stepper3.runToNewPosition(steps);
    stepper3.run();
    myStepper3->release();
                        }                        
  else if (stepper == 4){
    stepper4.runToNewPosition(steps);
    stepper4.run();
    myStepper4->release();
                        }
  else {Serial.println("stepper not recognised");}                    
      Serial.print("Filter no:");
      Serial.println(number); 
}

// Function to split the serial input
String getValue(String data, char separator, int index)
{
  int found = 0;
  int strIndex[] = {0, -1};
  int maxIndex = data.length()-1;

  for(int i=0; i<=maxIndex && found<=index; i++){
    if(data.charAt(i)==separator || i==maxIndex){
        found++;
        strIndex[0] = strIndex[1]+1;
        strIndex[1] = (i == maxIndex) ? i+1 : i;
    }
  }

  return found>index ? data.substring(strIndex[0], strIndex[1]) : "";
}
