const int ledPlantasVerde = 6;
const int ledZombiesRojo = 9;

const int botonBomba = 2;
const int botonVenganza = 13;

bool estadoAnteriorBomba = HIGH;
bool estadoAnteriorVenganza = HIGH;

String mensaje = "";

void setup() {
  Serial.begin(9600);
  pinMode(ledPlantasVerde, OUTPUT);

  pinMode(ledZombiesRojo, OUTPUT);

  pinMode(botonBomba, INPUT_PULLUP);
  pinMode(botonVenganza, INPUT_PULLUP);

  apagarLEDs();
}

void loop() {
  leerSerial();
  leerBotones();
}

void apagarLEDs() {
  analogWrite(ledPlantasVerde, 0);

  analogWrite(ledZombiesRojo, 0);
}

void leerSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n') {
      procesarMensaje(mensaje);
      mensaje = "";
    } else {
      mensaje += c;
    }
  }
}

void procesarMensaje(String msg) {
  // Formato esperado: A-P080-Z050
  if (!msg.startsWith("A-P")) return;

  int indiceZ = msg.indexOf("-Z");
  if (indiceZ == -1) return;

  String textoPlantas = msg.substring(3, indiceZ);
  String textoZombies = msg.substring(indiceZ + 2);

  int plantas = textoPlantas.toInt();
  int zombies = textoZombies.toInt();

  actualizarLEDs(plantas, zombies);
}

void actualizarLEDs(int plantas, int zombies) {
  plantas = constrain(plantas, 0, 999);
  zombies = constrain(zombies, 0, 999);

  int brilloPlantas = map(plantas, 0, 999, 0, 255);
  int brilloZombies = map(zombies, 0, 999, 0, 255);

  analogWrite(ledPlantasVerde, brilloPlantas);

  analogWrite(ledZombiesRojo, brilloZombies);
}

void leerBotones() {
  bool estadoBomba = digitalRead(botonBomba);
  bool estadoVenganza = digitalRead(botonVenganza);

  if (estadoAnteriorBomba == HIGH && estadoBomba == LOW) {
    Serial.println("B-1");
    delay(150);
  }

  if (estadoAnteriorVenganza == HIGH && estadoVenganza == LOW) {
    Serial.println("B-2");
    delay(150);
  }

  estadoAnteriorBomba = estadoBomba;
  estadoAnteriorVenganza = estadoVenganza;
}