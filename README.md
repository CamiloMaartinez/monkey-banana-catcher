# Monkey Banana Catcher
_Monkey Banana Catcher_

A retro game you control with your hands in front of a webcam. A neural network that we trained reads your gestures in real time.
_Un juego retro que se controla con las manos frente a una cámara web. Una red neuronal que entrenamos lee tus gestos en tiempo real._

- **Play it now in your browser (phone or computer):** https://monkey-banana-catcher.vercel.app/jugar/
  _Juégalo ya en el navegador (celular o computador): https://monkey-banana-catcher.vercel.app/jugar/_
- **Project presentation:** https://monkey-banana-catcher.vercel.app
  _Presentación del proyecto: https://monkey-banana-catcher.vercel.app_
- **Download the full PC game:** click the green **Code** button above → **Download ZIP**, or run `git clone https://github.com/CamiloMaartinez/monkey-banana-catcher`.
  _Descarga el juego completo para PC: haz clic en el botón verde **Code** de arriba → **Download ZIP**, o ejecuta `git clone https://github.com/CamiloMaartinez/monkey-banana-catcher`._

## Run the PC game in 4 steps
_Ejecuta el juego de PC en 4 pasos_

1. Install Python 3.12.
   _Instala Python 3.12._
2. Open a terminal in this folder and create the environment: `py -3.12 -m venv .venv` then `.venv\Scripts\activate` (Windows) or `python3.12 -m venv .venv` then `source .venv/bin/activate` (macOS / Linux).
   _Abre una terminal en esta carpeta y crea el entorno: `py -3.12 -m venv .venv` y luego `.venv\Scripts\activate` (Windows), o `python3.12 -m venv .venv` y luego `source .venv/bin/activate` (macOS / Linux)._
3. Install and download the hand model: `pip install -r requirements.txt` then `python download_model.py`.
   _Instala y descarga el modelo de la mano: `pip install -r requirements.txt` y luego `python download_model.py`._
4. Play: `python game.py`. Left index finger tilted = move, right-hand pinch = jump (or A / D / Space).
   _Juega: `python game.py`. Índice izquierdo inclinado = moverse, pinza con la mano derecha = saltar (o A / D / Espacio)._

## What is in this repository
_Qué hay en este repositorio_

| Folder | Content |
|---|---|
| `game.py`, `retro/` | The PC game (Pygame): 5 levels, tutorial, calibration. |
| `gestures/`, `train.py`, `evaluate.py` | Gesture pipeline (MediaPipe → features → MLP) and training. |
| `models/` | Our two trained networks (`left_mlp.pt`, `right_mlp.pt`). |
| `data/raw/` | The hand landmarks we recorded (numbers only, no images). |
| `web/` | The browser version and the presentation published on Vercel. |

_`game.py`, `retro/`: el juego de PC (Pygame) con 5 niveles, tutorial y calibración. `gestures/`, `train.py`, `evaluate.py`: el pipeline de gestos (MediaPipe → características → MLP) y el entrenamiento. `models/`: nuestras dos redes entrenadas. `data/raw/`: los landmarks de la mano que grabamos (solo números, sin imágenes). `web/`: la versión de navegador y la presentación publicadas en Vercel._

Team: Camilo, Jehis and María · Artificial Intelligence · Universidad Industrial de Santander.
_Equipo: Camilo, Jehis y María · Inteligencia Artificial · Universidad Industrial de Santander._

---

## Team guide (full details)
_Guía del equipo (detalles completos)_


A Pygame game controlled with the keyboard (A / D / Space) or with hand gestures. A trained neural network reads the gestures from MediaPipe hand landmarks.
_Un juego en Pygame que se controla con el teclado (A / D / Espacio) o con gestos de la mano. Una red neuronal entrenada lee los gestos a partir de los landmarks de MediaPipe._

## Status: Steps 3-4 (game ready)
_Estado: pasos 3-4 (juego listo)_

## Tech stack
_Tecnologías_

| Part | Choice | Why |
|---|---|---|
| Language | Python 3.12 | All libraries below support it. |
| Hand landmarks | MediaPipe 1.1.1 (Tasks API, `HandLandmarker`) | Fast on CPU, 21 points per hand, tells left from right. |
| Camera + drawing | OpenCV (installed by MediaPipe) | Standard for webcams. |
| Model (step 2) | PyTorch (CPU) | Clean install on Windows, light for a small MLP. |
| Game (step 4) | Pygame | Same as the reference project. |

_Lenguaje: Python 3.12, todas las librerías lo soportan. Landmarks: MediaPipe 1.1.1 (API Tasks, `HandLandmarker`), rápido en CPU, 21 puntos por mano, distingue izquierda y derecha. Cámara y dibujo: OpenCV (lo instala MediaPipe), estándar para webcams. Modelo (paso 2): PyTorch (CPU), instalación limpia en Windows y liviano para un MLP pequeño. Juego (paso 4): Pygame, igual que el proyecto de referencia._

**Important:** MediaPipe 1.x removed the old `mp.solutions.hands` API that most tutorials (and the TikTok video) use. This project uses the new Tasks API, so copy code from tutorials carefully.
_**Importante:** MediaPipe 1.x eliminó la API antigua `mp.solutions.hands` que usan la mayoría de tutoriales (y el video de TikTok). Este proyecto usa la nueva API Tasks, así que copien código de tutoriales con cuidado._

**Why PyTorch and not Keras:** I suggested Keras before. TensorFlow is a much heavier install on Windows and has more version conflicts. For a small MLP on CPU, PyTorch is the safer choice.
_**Por qué PyTorch y no Keras:** antes sugerí Keras. TensorFlow es una instalación mucho más pesada en Windows y tiene más conflictos de versiones. Para un MLP pequeño en CPU, PyTorch es la opción más segura._

## Setup (each of the 3 computers)
_Instalación (en cada uno de los 3 computadores)_

Windows (PowerShell), inside this folder:
_Windows (PowerShell), dentro de esta carpeta:_

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python download_model.py
python -m tests.test_pipeline
```

macOS / Linux: use `python3.12 -m venv .venv` and `source .venv/bin/activate`. On Linux you may also need `sudo apt install libegl1 libgles2`.
_macOS / Linux: usen `python3.12 -m venv .venv` y `source .venv/bin/activate`. En Linux puede que también necesiten `sudo apt install libegl1 libgles2`._

The last command must print `All checks passed.`
_El último comando debe imprimir `All checks passed.`_

## Gestures
_Gestos_

| Key | Hand | Label | Game action | How to do it |
|---|---|---|---|---|
| 1 | Left | `TILT_LEFT` | move left (A) | Index finger up, tilted clearly to your left (about 30° or more). |
| 2 | Left | `NEUTRAL` | stop | Index finger pointing straight up. |
| 3 | Left | `TILT_RIGHT` | move right (D) | Index finger up, tilted clearly to your right. |
| 4 | Right | `OPEN` | nothing | Any hand that is NOT pinching: open, relaxed, half closed. |
| 5 | Right | `PINCH` | jump (Space) | Thumb tip touching index tip. |

_1, izquierda, `TILT_LEFT`, mover a la izquierda (A): índice arriba, inclinado claramente a tu izquierda (unos 30° o más). 2, izquierda, `NEUTRAL`, detenerse: índice apuntando recto hacia arriba. 3, izquierda, `TILT_RIGHT`, mover a la derecha (D): índice arriba, inclinado claramente a tu derecha. 4, derecha, `OPEN`, nada: cualquier mano que NO esté haciendo pinza: abierta, relajada, medio cerrada. 5, derecha, `PINCH`, saltar (Espacio): punta del pulgar tocando la punta del índice._

`OPEN` is the "no jump" class, so record many different non-pinch shapes. If it only has perfect open hands, the model will jump by mistake when the hand relaxes.
_`OPEN` es la clase "no saltar", así que graben muchas formas distintas que no sean pinza. Si solo tiene manos perfectamente abiertas, el modelo saltará por error cuando la mano se relaje._

## Recording the dataset
_Grabar el dataset_

```powershell
python capture.py --user camilo --session s1
```

In the camera window: choose a gesture with `1`-`5`, press `SPACE`, hold the gesture during the countdown and the recording (150 frames, about 5 s). `Z` deletes the last take, `X` cancels the current take, `Q` quits.
_En la ventana de la cámara: elijan un gesto con `1`-`5`, presionen `SPACE`, mantengan el gesto durante la cuenta regresiva y la grabación (150 frames, unos 5 s). `Z` borra la última toma, `X` cancela la toma actual, `Q` sale._

Only frames where the correct hand is visible are saved (green skeleton). A gray skeleton is a hand that is ignored.
_Solo se guardan los frames donde se ve la mano correcta (esqueleto verde). Un esqueleto gris es una mano que se ignora._

**Plan per person:** 3 sessions (`s1`, `s2`, `s3`), each in a different place or light, and in each session 1 take of each of the 5 gestures. That is 5 takes per session, about 2 minutes.
_**Plan por persona:** 3 sesiones (`s1`, `s2`, `s3`), cada una en un lugar o con luz distinta, y en cada sesión 1 toma de cada uno de los 5 gestos. Son 5 tomas por sesión, unos 2 minutos._

**Target:** 3 people x 5 gestures x 450 frames = about 6,750 rows.
_**Meta:** 3 personas x 5 gestos x 450 frames = unas 6.750 filas._

**During each take, move a little:** different positions in the image, closer and farther (40 to 100 cm), small turns of the wrist. This variation is what makes the model work for other people.
_**Durante cada toma, muévanse un poco:** distintas posiciones en la imagen, más cerca y más lejos (40 a 100 cm), pequeños giros de la muñeca. Esta variación es lo que hace que el modelo funcione con otras personas._

Check progress at any time:
_Revisen el avance en cualquier momento:_

```powershell
python check_dataset.py
```

Each person sends their `data/raw/<user>/` folder to the team (or commits it to the shared repo).
_Cada persona envía su carpeta `data/raw/<usuario>/` al equipo (o la sube al repositorio compartido)._

## How the data is stored
_Cómo se guardan los datos_

- One CSV per person and session: `data/raw/<user>/<session>.csv`.
  _Un CSV por persona y sesión: `data/raw/<usuario>/<sesión>.csv`._
- One row = one hand in one frame: `timestamp, user, session, take, frame, hand, label, hand_score, img_w, img_h`, then `x0, y0, z0 ... x20, y20, z20`.
  _Una fila = una mano en un frame: `timestamp, user, session, take, frame, hand, label, hand_score, img_w, img_h`, luego `x0, y0, z0 ... x20, y20, z20`._
- We save the **raw** landmarks. Normalization (`gestures/landmarks.py: normalize`) runs at training time and in the game, so we can improve it without recording again.
  _Guardamos los landmarks **crudos**. La normalización (`gestures/landmarks.py: normalize`) se aplica al entrenar y en el juego, así podemos mejorarla sin volver a grabar._
- Normalization: wrist moved to (0, 0), divided by the wrist to middle-finger-base distance. It does **not** remove rotation, because the tilt is exactly what the model must see.
  _Normalización: la muñeca se lleva a (0, 0) y se divide por la distancia muñeca a base del dedo medio. **No** quita la rotación, porque la inclinación es justo lo que el modelo debe ver._
- The image is mirrored (selfie view) before detection. That way MediaPipe's "Left" is your real left hand.
  _La imagen se voltea (vista selfie) antes de la detección. Así el "Left" de MediaPipe es tu mano izquierda real._

## Two-week schedule
_Cronograma de dos semanas_

| Days | Step |
|---|---|
| 1-3 | Setup on the 3 computers, record the dataset. |
| 4-7 | Train the two MLPs, compare with the rule-based method, test on an unseen person. |
| 8-10 | Real-time inference with smoothing, Pygame game. |
| 11-14 | Measure accuracy, latency and FPS, write the report, rehearse the demo. |

_Días 1-3: instalación en los 3 computadores, grabar el dataset. Días 4-7: entrenar los dos MLP, comparar con el método de reglas, probar con una persona no vista. Días 8-10: inferencia en tiempo real con suavizado, juego en Pygame. Días 11-14: medir precisión, latencia y FPS, escribir el informe, ensayar la demo._

## Training (step 2)
_Entrenamiento (paso 2)_

```powershell
pip install -r requirements.txt   # adds PyTorch
python train.py
```

For each hand it tests the MLP and the rule-based method on a person (or session) the model never saw, prints the accuracy and confusion matrix, then trains the final model on all data and saves it in `models/left_mlp.pt` and `models/right_mlp.pt`. Reports go to `reports/`.
_Para cada mano prueba el MLP y el método de reglas con una persona (o sesión) que el modelo no vio, imprime la precisión y la matriz de confusión, luego entrena el modelo final con todos los datos y lo guarda en `models/left_mlp.pt` y `models/right_mlp.pt`. Los reportes quedan en `reports/`._

Why not split frames randomly: frames of the same take are almost identical, so a random split leaks the answer and gives a fake high accuracy.
_Por qué no dividir los frames al azar: los frames de una misma toma son casi idénticos, así que una división al azar filtra la respuesta y da una precisión falsamente alta._

Model: MLP `features → 128 → 64 → classes` with BatchNorm, ReLU and Dropout 0.3, Adam, class weights, and augmentation (rotation, scale, noise) every epoch. Features: left hand = direction of the index finger (8 numbers), right hand = fingertip distances divided by palm size (10 numbers). `python train.py --features raw` uses all 63 landmark numbers instead, for comparison (see `reports/experiments-2026-11-04.md`: raw overfits to each person's hand).
_Modelo: MLP `features → 128 → 64 → clases` con BatchNorm, ReLU y Dropout 0.3, Adam, pesos por clase, y aumento de datos (rotación, escala, ruido) en cada época. Features: mano izquierda = dirección del dedo índice (8 números), mano derecha = distancias entre puntas de dedos divididas por el tamaño de la palma (10 números). `python train.py --features raw` usa los 63 números de los landmarks, para comparar (ver `reports/experiments-2026-11-04.md`: con raw el modelo se sobreajusta a la mano de cada persona)._

## Play (steps 3-4)
_Jugar (pasos 3-4)_

```powershell
pip install -r requirements.txt   # adds Pygame (no new packages for the retro version)
python game.py
```

Retro pixel-art game. The title menu has **PLAY / TUTORIAL / CALIBRATE / SETTINGS**. Keyboard (A / D / SPACE) and gestures work at the same time, also in the menus: tilt to choose, pinch to confirm.
_Juego retro pixel-art. El menú principal tiene **JUGAR / TUTORIAL / CALIBRAR / AJUSTES**. El teclado (A / D / ESPACIO) y los gestos funcionan al mismo tiempo, también en los menús: inclina para escoger, pellizca para confirmar._

- **Levels:** Tutorial, 5 levels (Jungle Morning, Sunny Beach, Sunset Canyon, Moonlit Jungle, Volcano Peak) and Endless (∞). In levels 1-5, catch the goal before the timer ends; coconuts, bouncing coconuts and rocks cost a heart, birds steal bananas. Endless has no timer, every miss costs a heart and the speed keeps rising; the best 10 scores are saved in `highscores.json`.
  _**Niveles:** Tutorial, 5 niveles y Sin fin (∞). En los niveles 1-5, atrapa la meta antes de que acabe el tiempo; los cocos, los cocos que rebotan y las rocas quitan un corazón, los pájaros roban bananos. Sin fin no tiene tiempo, cada banano perdido quita un corazón y la velocidad sube; los 10 mejores puntajes se guardan en `highscores.json`._
- **Power-ups (levels 2+):** magnet (pulls bananas), slow motion, shield (blocks one hit), extra heart.
  _**Poderes (niveles 2+):** imán (atrae bananos), cámara lenta, escudo (bloquea un golpe), corazón extra._
- **Tutorial:** six steps, one gesture at a time; the next step starts only when the camera sees the current gesture.
  _**Tutorial:** seis pasos, un gesto a la vez; el siguiente paso empieza solo cuando la cámara ve el gesto actual._
- **Calibrate:** type your name, hold each of the 5 gestures for about 3 seconds, and the game trains your personal model in the background (about 10 s on a laptop CPU). It shows the accuracy **before and after** on frames the network did not train on, and never replaces a model with a worse one. Your frames are also saved in `data/raw/<name>/cal_<date>.csv`.
  _**Calibrar:** escribe tu nombre, sostén cada uno de los 5 gestos unos 3 segundos y el juego entrena tu modelo personal en segundo plano (unos 10 s en la CPU de un portátil). Muestra la precisión **antes y después** en frames con los que la red no entrenó, y nunca cambia un modelo por uno peor. Tus frames también se guardan en `data/raw/<nombre>/cal_<fecha>.csv`._
- **Settings** (saved in `settings.json`): difficulty Easy / Normal / Hard, language English / Español, sound, music, control network / rules. With the camera on, coconuts and rocks warn 0.4 s earlier, and a jump pressed just before landing still counts, because gestures arrive a bit later than keys.
  _**Ajustes** (se guardan en `settings.json`): dificultad Fácil / Normal / Difícil, idioma, sonido, música, control red / reglas. Con la cámara, los cocos y las rocas avisan 0.4 s antes, y un salto pedido justo antes de aterrizar sigue contando, porque los gestos llegan un poco después que las teclas._
- **AI on screen:** the right panel shows the camera, the move and jump lamps, the raw network output and a live confidence graph (green = left hand, yellow = right hand, dashed line = 70%). After each level, an **AI STATS** box shows how often a hand was seen, how often the network was sure, the average reaction time and the number of pinches.
  _**IA en pantalla:** el panel derecho muestra la cámara, las luces de mover y saltar, la salida cruda de la red y una gráfica de confianza en vivo (verde = mano izquierda, amarillo = mano derecha, línea punteada = 70%). Después de cada nivel, el recuadro **AI STATS** muestra qué tanto se vio cada mano, qué tanto la red estuvo segura, el tiempo de reacción promedio y el número de pellizcos._

Keys: P pause, M sound, N music, L language, R network/rules, F11 full screen, ESC back. Screenshots: `docs/screens/`.
_Teclas: P pausa, M sonido, N música, L idioma, R red/reglas, F11 pantalla completa, ESC atrás. Capturas: `docs/screens/`._

| Command | What it does |
|---|---|
| `python game.py` | Neural network models. |
| `python game.py --rules` | Backup: fixed rules (use it if the network fails on demo day). |
| `python game.py --no-camera` | Keyboard only. |
| `python game.py --player ana` | Ana's calibrated models. |

_`python game.py`: modelos de red neuronal. `python game.py --rules`: respaldo con reglas fijas (úsenlo si la red falla el día de la demo). `python game.py --no-camera`: solo teclado. `python game.py --player ana`: modelos calibrados de Ana._

**Smoothing:** a command changes only when 3 of the last 5 frames agree and the model is at least 70% sure. A jump fires once per new pinch.
_**Suavizado:** un comando cambia solo cuando 3 de los últimos 5 frames coinciden y el modelo está al menos 70% seguro. Un salto se dispara una vez por cada pinza nueva._

**Calibration from the command line (same result as CALIBRATE in the game):**
_**Calibración desde la consola (mismo resultado que CALIBRAR en el juego):**_

```powershell
python capture.py --user ana --session cal   # 1 take of each gesture (1..5, SPACE)
python calibrate.py --user ana
python game.py --player ana
```

**Measurements for the report:** when you close the game, it prints and saves `reports/play_<date>.json` with camera FPS, average latency and how often each gesture was detected.
_**Mediciones para el informe:** al cerrar el juego, imprime y guarda `reports/play_<fecha>.json` con los FPS de la cámara, la latencia promedio y cuántas veces se detectó cada gesto._

## Extra gestures (rules, no training data yet)
_Gestos extra (reglas, todavía sin datos de entrenamiento)_

| Gesture | Action | Keyboard |
|---|---|---|
| Left fist, held 0.6 s | Pause / resume | P |
| Right hand swipe sideways (open hand) | Dash to that side | SHIFT |

_Puño izquierdo sostenido 0.6 s: pausa / reanudar (teclado P). Deslizar la mano derecha abierta de lado: impulso hacia ese lado (teclado SHIFT)._

They live in `gestures/extra.py`. Checked on the recorded data: the fist shape appears in under 1% of normal gesture frames and needs 0.6 s held, and the swipe threshold (30% of the image width in 0.3 s) gave about 0.7 accidental swipes per minute.
_Están en `gestures/extra.py`. Revisado con los datos grabados: la forma de puño aparece en menos del 1% de los frames de gestos normales y debe sostenerse 0.6 s, y el umbral del deslizamiento (30% del ancho de la imagen en 0.3 s) dio unos 0.7 deslizamientos accidentales por minuto._

## Learning from mistakes (active learning)
_Aprender de los errores (aprendizaje activo)_

While you play with the camera, every frame where the network is less than 70% sure is saved in `data/doubts/<player>/` (at most 1,500 per game, one every 0.3 s per hand). The side panel shows how many. Afterwards:
_Mientras juegas con la cámara, cada frame donde la red está menos de 70% segura se guarda en `data/doubts/<jugador>/` (máximo 1.500 por partida, uno cada 0.3 s por mano). El panel lateral muestra cuántos. Después:_

```powershell
python review_doubts.py --player camilo   # shows each hand as a skeleton; press 1-5 for the right gesture, X to skip
python train.py                           # retrain with the corrected frames
```

The corrected frames go to `data/raw/<player>/review_<date>.csv`, so they count like any recorded session.
_Los frames corregidos van a `data/raw/<jugador>/review_<fecha>.csv`, así que cuentan como cualquier sesión grabada._

**Testing a 4th person:** record them with `python capture.py --user <name> --session s1`, then run `python evaluate.py`. Every evaluation is leave-one-person-out, so the new person automatically becomes a test case.
_**Probar con una 4.ª persona:** grábenla con `python capture.py --user <nombre> --session s1` y luego ejecuten `python evaluate.py`. Toda la evaluación deja una persona por fuera, así que la persona nueva se vuelve un caso de prueba automáticamente._

## Evaluation for the report
_Evaluación para el informe_

```powershell
pip install -r requirements-eval.txt   # scikit-learn + matplotlib, only for these two scripts
python evaluate.py      # rules vs kNN vs SVM vs Random Forest vs MLP, learning curve, false triggers, speed
python temporal.py      # MLP per frame vs MLP + vote vs GRU over 8 frames: accuracy, flicker, delay
```

Results and charts go to `reports/evaluation/` (`evaluation.md`, `temporal.md`, PNG charts).
_Los resultados y las gráficas quedan en `reports/evaluation/` (`evaluation.md`, `temporal.md`, gráficas PNG)._

## Windows .exe
_Ejecutable de Windows_

```powershell
..\.venv\Scripts\Activate.ps1
.\build_exe.ps1        # -> dist\MonkeyBananaCatcher\MonkeyBananaCatcher.exe (zip the whole folder to share)
```

The folder is about 1 GB because PyTorch and MediaPipe are inside. Models, team data and save files sit next to the `.exe`.
_La carpeta pesa más o menos 1 GB porque PyTorch y MediaPipe van adentro. Los modelos, los datos del equipo y los archivos de guardado quedan junto al `.exe`._

## Files
_Archivos_

| File | What it does |
|---|---|
| `gestures/config.py` | Classes, keys, paths, capture settings. |
| `gestures/landmarks.py` | MediaPipe hand tracker and `normalize`. |
| `gestures/dataset.py` | CSV format and writer. |
| `capture.py` | Recording tool. |
| `check_dataset.py` | Counts rows per person and gesture, lists what is missing. |
| `download_model.py` | Downloads the MediaPipe hand model. |
| `tests/test_pipeline.py` | Checks that work without a webcam. |
| `train.py` | Evaluates and trains the two MLPs. |
| `gestures/model.py` | The MLP, save/load, `GesturePredictor`. |
| `gestures/features.py` | Loads CSVs, normalizes, augmentation. |
| `gestures/rules.py` | Rule-based baseline (thresholds). |
| `tests/make_fake_data.py` | Fake dataset to test `train.py` without recording. |
| `game.py` | The game. |
| `gestures/controller.py` | Camera thread, model, smoothing, commands. |
| `calibrate.py` | Personal models for one player. |
| `delete_take.py` | Removes a wrong take from a session. |
| `retro/levels.py` | The 5 levels: colours, goal, speeds, hazards. Edit here to tune difficulty. |
| `retro/sprites.py` | Pixel-art sprites as text grids (monkey, banana, coconut, hearts, stars). |
| `retro/scenery.py` | Generated backgrounds: dithered sky, parallax hills, ground, ambient life. |
| `retro/font.py`, `retro/sfx.py`, `retro/effects.py` | Pixel font, chiptune sounds and music, particles and screen shake. |
| `retro/entities.py` | Everything that moves: monkey, bananas, coconuts, rocks, birds, power-ups. |
| `retro/tutorial.py`, `retro/calibration.py` | Tutorial steps; in-game calibration screen. |
| `retro/panel.py`, `retro/stats.py` | Right panel with the live confidence graph; AI stats per level. |
| `retro/i18n.py`, `retro/save.py` | English/Spanish texts; settings, progress and top 10 files. |
| `gestures/personal.py` | Trains a personal model from the in-game calibration (before/after accuracy). |
| `gestures/extra.py` | Fist (pause) and swipe (dash) detection with simple rules. |
| `review_doubts.py` | Relabel the frames the network was unsure about while playing. |
| `evaluate.py`, `temporal.py` | Model comparison and temporal (GRU) experiment for the report. |
| `build_exe.ps1` | Builds the Windows `.exe`. |

_`gestures/config.py`: clases, teclas, rutas, ajustes de captura. `gestures/landmarks.py`: detector de manos de MediaPipe y `normalize`. `gestures/dataset.py`: formato y escritura del CSV. `capture.py`: herramienta de grabación. `check_dataset.py`: cuenta filas por persona y gesto, lista lo que falta. `download_model.py`: descarga el modelo de manos de MediaPipe. `tests/test_pipeline.py`: pruebas que funcionan sin webcam. `train.py`: evalúa y entrena los dos MLP. `gestures/model.py`: el MLP, guardar/cargar, `GesturePredictor`. `gestures/features.py`: carga CSV, normaliza, aumento de datos. `gestures/rules.py`: método base de reglas (umbrales). `tests/make_fake_data.py`: dataset falso para probar `train.py` sin grabar. `game.py`: el juego. `gestures/controller.py`: hilo de cámara, modelo, suavizado, comandos. `calibrate.py`: modelos personales para un jugador. `delete_take.py`: borra una toma equivocada de una sesión. `retro/levels.py`: los 5 niveles (colores, meta, velocidades, obstáculos); editen aquí para ajustar la dificultad. `retro/sprites.py`: sprites pixel-art como cuadrículas de texto. `retro/scenery.py`: fondos generados (cielo con dithering, colinas con parallax, suelo, vida ambiental). `retro/font.py`, `retro/sfx.py`, `retro/effects.py`: fuente pixel, sonidos y música chiptune, partículas y temblor de pantalla. `retro/entities.py`: todo lo que se mueve. `retro/tutorial.py`, `retro/calibration.py`: pasos del tutorial y pantalla de calibración. `retro/panel.py`, `retro/stats.py`: panel derecho con la gráfica de confianza y estadísticas de IA por nivel. `retro/i18n.py`, `retro/save.py`: textos inglés/español; archivos de ajustes, progreso y top 10. `gestures/personal.py`: entrena el modelo personal de la calibración del juego. `gestures/extra.py`: detección de puño (pausa) y deslizamiento (impulso) con reglas simples. `review_doubts.py`: reetiquetar los frames dudosos del juego. `evaluate.py`, `temporal.py`: comparación de modelos y experimento temporal (GRU) para el informe. `build_exe.ps1`: crea el `.exe` de Windows._
