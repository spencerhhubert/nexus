#include <ArduinoSTL.h>
#include <Adafruit_PWMServoDriver.h>
#include <map>

std::map<String, int> myDictionary;

int led = 12;

void setup() {
  pinMode(led, OUTPUT);
}

void loop() {
  digitalWrite(led, HIGH);
  delay(1000);
  digitalWrite(led, LOW);
  delay(1000);
}
