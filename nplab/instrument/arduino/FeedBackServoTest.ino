// https://learn.adafruit.com/analog-feedback-servos/using-feedback
// This code runs a calibration function on startup and has a angle hardcoded.
// Using PWM pin 9 and feedback on pin A1
// The two servo outputs on the UNO board are wired to pins 9 & 10 so they can not be used for anything else.
// The servo is using the power supply from the arduino without an external supply.

#include <Servo.h> 
 
Servo myservo;  

// Control and feedback pins
int servoPin = 9;
int feedbackPin = A1;

// Calibration values
int minDegrees;
int maxDegrees;
int minFeedback;
int maxFeedback;
int tolerance = 2; // max feedback measurement error

/*
  This function establishes the feedback values for 2 positions of the servo.
  With this information, we can interpolate feedback values for intermediate positions
*/
void calibrate(Servo servo, int analogPin, int minPos, int maxPos)
{
  // Move to the minimum position and record the feedback value
  servo.write(minPos);
  minDegrees = minPos;
  delay(2000); // make sure it has time to get there and settle
  minFeedback = analogRead(analogPin);
  
  // Move to the maximum position and record the feedback value
  servo.write(maxPos);
  maxDegrees = maxPos;
  delay(2000); // make sure it has time to get there and settle
  maxFeedback = analogRead(analogPin);
}
 
void setup() 
{ 
  Serial.begin(9600);
  myservo.attach(servoPin); 
  
  Serial.println("Claibrating");
  calibrate(myservo, feedbackPin, 20, 160);  // calibrate for the 20-160 degree range
  Serial.println("Claibrated");
} 

void loop()
{

// Seeking to a position
Serial.println();
Seek(myservo, feedbackPin, 60);
Serial.print("Servo seek angle = ");
Serial.println(getPos(feedbackPin));
delay(1000);

// Display servo position
Serial.print("Servo angle = ");
Serial.println(getPos(feedbackPin));
delay(1000);


Serial.print("max = ");
Serial.println(maxFeedback);
Serial.print("min = ");
Serial.println(minFeedback);

}

int getPos(int analogPin)
{
  return map(analogRead(analogPin), minFeedback, maxFeedback, minDegrees, maxDegrees);
}

void Seek(Servo servo, int analogPin, int pos)
{
  // Start the move...
  servo.write(pos);
  
  // Calculate the target feedback value for the final position
  int target = map(pos, minDegrees, maxDegrees, minFeedback, maxFeedback); 
  
  // Wait until it reaches the target
  while(abs(analogRead(analogPin) - target) > tolerance){} // wait...
}
