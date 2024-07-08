int pot1, pot2, pot3, pot4;
int lastpot1 = -1;
int lastpot2 = -1;
int lastpot3 = -1;
int lastpot4 = -1;
void setup() {
  Serial.begin(9600);
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(A2, INPUT);
  pinMode(A3, INPUT);

}

void loop() {
pot1 = analogRead(A0);
pot2 = analogRead(A1);
pot3 = analogRead(A2);
pot4 = analogRead(A3);


if (pot1 < 2){
  pot1 = 0;
}
if (pot2 < 2){
  pot2 = 0;
}
if (pot3 < 2){
  pot3 = 0;
}
if (pot4 < 2){
  pot4 = 0;
}

if((pot1 != lastpot1) || (pot2 != lastpot2) || (pot3 != lastpot3) || (pot4 != lastpot4)){
Serial.println(String(pot1) + "|" + String(pot2) + "|" + String(pot3) + "|" + String(pot4));
lastpot1 = pot1;
lastpot2 = pot2; 
lastpot3 = pot3; 
lastpot4 = pot4;
}

delay(100);
}
