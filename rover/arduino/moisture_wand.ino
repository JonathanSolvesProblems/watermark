/*
 * Watermark moisture wand (Arduino Uno, from the RenoScout build).
 *
 * Mounted low on the rover's nose. Three parts from the Smraza kit:
 *   - DHT11 temperature/humidity     -> room conditions at the water's edge
 *   - Water-level sensor (analog)    -> the STOP: the rover halts when this reads wet
 *   - HC-SR04 ultrasonic             -> distance to whatever is ahead
 *
 * Prints one CSV line per second over USB serial, read by rover/wand.py:
 *   millis,humidity_pct,temp_c,water_raw,distance_cm
 *
 * Library: "DHT sensor library" by Adafruit (Library Manager).
 * Wiring:  DHT11 data -> D2   Water sensor S -> A0   HC-SR04 TRIG -> D9, ECHO -> D10
 * All grounds common. The water sensor's probe hangs 2 to 3 mm above the floor.
 */
#include <DHT.h>

#define DHT_PIN   2
#define DHT_TYPE  DHT11
#define WATER_PIN A0
#define TRIG_PIN  9
#define ECHO_PIN  10

DHT dht(DHT_PIN, DHT_TYPE);

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(WATER_PIN, INPUT);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  Serial.println("millis,humidity_pct,temp_c,water_raw,distance_cm");
}

long readDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long dur = pulseIn(ECHO_PIN, HIGH, 30000UL);  // 30 ms timeout (~5 m)
  return dur == 0 ? -1 : dur / 58;               // us -> cm
}

void loop() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int water = analogRead(WATER_PIN);
  long dist = readDistanceCm();

  Serial.print(millis());              Serial.print(",");
  Serial.print(isnan(h) ? -1 : h);     Serial.print(",");
  Serial.print(isnan(t) ? -99 : t);    Serial.print(",");
  Serial.print(water);                 Serial.print(",");
  Serial.println(dist);
  delay(1000);
}
