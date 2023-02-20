// operated an electromagnet through arduino with relay shield.
// the relay shield has 4 relays which enable the magnetic field to be either North, South or Zero
// the electromagnet should be switched off in python command before controlling function shuts down
// each relay has two states: NC - normally closed - ie connected at zero(LOW) voltage and disconnected at HIGH voltage
// and NO - normally open - i.e. disconnected at zero(LOW) voltage and connected at HIGH voltage.
// connecting the relays in a specific way allows to select the polarity and have an ON/OFF master switch (this is relay 1)

// these are the relay assignments:
int relay_1 = 4; //master ON/OFF switch
int relay_2 = 5;
int relay_3 = 6; //broken and not used in this specific device
int relay_4 = 7;
// status variable:
String state="Z";

void setup() {
  // start COM connection and arduino pin assignment:
  Serial.begin(9600);
  pinMode(relay_1, OUTPUT);
  pinMode(relay_2, OUTPUT);
  pinMode(relay_3, OUTPUT);
  pinMode(relay_4, OUTPUT);
    
}


void loop() {
  //HIGH=NO connected!
  // 'positive' field
  if (Serial.available()>0) {
    char msg = Serial.read();
    switch (msg) {
    case 'N': //north
      digitalWrite(relay_1, LOW);
      digitalWrite(relay_2, LOW);
      digitalWrite(relay_4, LOW);
      digitalWrite(relay_1, HIGH);
      state="N";
      Serial.println(state+"\n");
      break;
    case 'S': //south
      digitalWrite(relay_1, LOW);
      digitalWrite(relay_2, HIGH);
      digitalWrite(relay_4, HIGH);
      digitalWrite(relay_1, HIGH);    
      state="S";
      Serial.println(state+"\n");
      break;
    case 'Z': //zero
      digitalWrite(relay_1, LOW);
      state="Z";
      Serial.println(state+"\n");
      break;
    case 's':    // status check    
      Serial.println(state+"\n");
      break;
    default: //bad command - works like status check
      Serial.println(state+"\n");
      break;
    }
    
  }
}
