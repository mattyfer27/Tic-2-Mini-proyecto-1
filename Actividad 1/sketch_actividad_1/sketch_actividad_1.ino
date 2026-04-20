// PINES
const int NUM_BOTONES = 5; 
const int botones[] = {2, 3, 4, 5, 12}; 
const int leds[] = {A1, 9, 10, 11, 6};  
const int pinBuzzer = 8;

// VARIABLES DE JUEGO
int botonPerdedor;
bool botonUsado[6];
int racha = 0; 
long puntaje = 0;
unsigned long tiempoUltimaAccion;
int tiempoLimiteActual = 5000;

void setup() {
  Serial.begin(9600);
  for (int i = 0; i < NUM_BOTONES; i++) {
    pinMode(botones[i], INPUT_PULLUP);
    pinMode(leds[i], OUTPUT);
    digitalWrite(leds[i], LOW);
    botonUsado[i] = false;
  }
  pinMode(pinBuzzer, OUTPUT);
  randomSeed(analogRead(0));
  botonPerdedor = random(0, NUM_BOTONES);
  
  // DIFICULTAD POR RACHA: Cada victoria quita 500ms (mínimo 1.5 seg)
  tiempoLimiteActual = 5000 - (racha * 500);
  if (tiempoLimiteActual < 1500) tiempoLimiteActual = 1500;

  tiempoUltimaAccion = millis(); 
  
  Serial.println("\n========================");
  Serial.print("   RACHA ACTUAL: "); Serial.println(racha);
  Serial.print("   TIEMPO: "); Serial.print(tiempoLimiteActual / 1000.0); Serial.println("s");
  Serial.println("========================");
}

void loop() {
  // 1. DERROTA POR TIEMPO
  if (millis() - tiempoUltimaAccion > tiempoLimiteActual) {
    Serial.println("MUY LENTO, RACHA PERDIDA");
    sonidoDerrota(); 
    racha = 0; // Se resetea la racha
    puntaje = 0; 
    parpadeoVisualSolo(leds[botonPerdedor], 150); 
    reiniciarRonda();
    return; 
  }

  // 2. REVISAR BOTONES
  for (int i = 0; i < NUM_BOTONES; i++) {
    if (digitalRead(botones[i]) == LOW && !botonUsado[i]) {
      delay(50); 
      if (digitalRead(botones[i]) == LOW) {
        
        if (i == botonPerdedor) {
          // DERROTA POR BOMBA
          Serial.print("¡BOOM! PERDISTE TU RACHA DE "); Serial.println(racha);
          sonidoExplosion();
          racha = 0; // Se resetea la racha
          puntaje = 0;
          parpadeoVisualSolo(leds[i], 40); 
          reiniciarRonda();
          return;
        } 
        else {
          // ACIERTO
          tone(pinBuzzer, 1500 + (racha * 100), 80); // El tono sube con la racha
          digitalWrite(leds[i], HIGH);
          botonUsado[i] = true;
          puntaje += 10;
          tiempoUltimaAccion = millis(); 
          verificarVictoria();
        }
      }
    }
  }
}

// SONIDOS
void sonidoExplosion() {
  for (int f = 400; f > 100; f -= 20) {
    tone(pinBuzzer, f, 50); delay(50);
  }
  noTone(pinBuzzer);
}

void sonidoDerrota() {
  tone(pinBuzzer, 150, 400); delay(450);
  tone(pinBuzzer, 100, 600); delay(650);
}

// VISUAL
void parpadeoVisualSolo(int pinLed, int velocidad) {
  for (int i = 0; i < 8; i++) {
    digitalWrite(pinLed, HIGH); delay(velocidad);
    digitalWrite(pinLed, LOW); delay(velocidad);
  }
}

// LÓGICA
void verificarVictoria() {
  int aciertos = 0;
  for(int i=0; i < NUM_BOTONES; i++) { if(botonUsado[i]) aciertos++; }
  
  if(aciertos == NUM_BOTONES - 1) { 
    racha++;
    puntaje += 50;
    
    Serial.println("¡RONDA SUPERADA!");
    
    // Melodía racha
    tone(pinBuzzer, 523, 100); delay(120);
    tone(pinBuzzer, 659, 100); delay(120);
    tone(pinBuzzer, 784, 100); delay(120);
    tone(pinBuzzer, 1046, 200); delay(250);
    if(racha >= 3) { tone(pinBuzzer, 1200, 150); delay(150); } // Sonido extra por combo
    
    reiniciarRonda();
  }
}

void reiniciarRonda() {
  for(int i=0; i < 6; i++) digitalWrite(leds[i], LOW);
  delay(1000);
  setup(); 
}