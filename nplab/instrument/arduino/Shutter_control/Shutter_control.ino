int shutterPin = 2;
void setup() {
  pinMode(shutterPin,OUTPUT);
  Serial.begin(9600);
  // put your setup code here, to run once:

}

void loop() {
  while (Serial.available()==0)  {
    String command_str = Serial.readString();
    if (command_str == "Open\n"){
      digitalWrite(shutterPin,HIGH);
    }
    else if (command_str == "Closed\n") {
      digitalWrite(shutterPin,LOW);
    }
    else if (command_str == "Read\n"){
      if (digitalRead(shutterPin)==LOW){
        Serial.println("Closed\n");
      }
      else if (digitalRead(shutterPin)==HIGH){
        Serial.println("Open\n");
      }
    }
  }
}
