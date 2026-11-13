# Experiments, 2026-11-04 (2 people: camilo 1 session, jehis 3 sessions)

Test = leave-one-person-out (train on one person, test on the other). Accuracy, mean of the 2 folds.

| Hand | Method | Accuracy |
|---|---|---|
| Left | Rules (index angle, 20° threshold) | 79.6% |
| Left | MLP, raw landmarks x,y,z (current train.py) | 59.8% |
| Left | MLP, raw landmarks + finger-length augmentation | 66.2% |
| Left | MLP, index-finger direction features only | 79.6% |
| Left | MLP raw landmarks + 1 calibration take per gesture of the new person | **91.0%** |
| Right | Rules (thumb-index distance / palm) | 94.2% |
| Right | MLP, raw landmarks x,y,z | 86.8% |
| Right | MLP, pinch distance features | 93.5% |
| Right | MLP pinch features + 1 calibration take per gesture | **97.2%** |

Same person, unseen takes (camilo only): MLP 98.7% left, 100% right.

Findings
- With only 1 training person, the MLP on raw landmarks learns person-specific hand shape (palm orientation, z scale: mean |z| 0.33 vs 0.22) instead of the gesture.
- Hand-picked features (index direction, fingertip distances) generalize like the rules.
- A short per-user calibration (one 5 s take per gesture) beats the rules on both hands.
- Jehis s1/s3 TILT_RIGHT takes are small tilts (11-17°), correct direction, kept.

# Update: 3 people (camilo 1 session, jehis 3, maria 3)

Leave-one-person-out (train on 2 people, test on the 3rd), mean of 3 folds.

| Hand | Method | camilo | jehis | maria | Mean |
|---|---|---|---|---|---|
| Left | Rules (20° threshold) | 75.5% | 83.7% | 93.0% | 84.0% |
| Left | MLP raw 63 landmarks | | | | 71.7% |
| Left | **MLP index-direction features (final)** | 78.5% | 88.3% | 90.4% | **85.8%** |
| Left | MLP index features + calibration take | | | | 85.9% |
| Right | Rules (distance threshold) | 90.7% | 99.6% | 95.3% | 94.5% |
| Right | MLP raw 63 landmarks | | | | 87.0% |
| Right | **MLP fingertip-distance features (final)** | 86.0% | 99.6% | 97.7% | **93.2%** |
| Right | MLP pinch features + calibration take | | | | 97.2% |

Decision: train.py now uses hand-specific features by default (`--features raw` keeps the old input for comparison).
With 3 people, calibration still helps the right hand (+4 points) but barely the left hand.
Remaining left-hand errors are mostly small tilts that look NEUTRAL (label ambiguity), and camilo's single session.

## Update: new lighting data (Zapata = jehis, Mafe = maria)
_Actualización: nuevos datos con iluminación (Zapata = jehis, Mafe = maria)_

New sessions recorded at the training place, with front light and backlight: jehis s4, s5, s1luz; maria s4 (sent as `s1`, renamed because `maria/s1` already existed), s1luz. 22,500 new rows. 5 takes were removed because the finger pointed the wrong way for the label (jehis s1luz take 11; jehis s5 takes 5, 16, 18, 20).
_Nuevas sesiones grabadas en el lugar de entrenamiento, con luz de frente y contraluz: jehis s4, s5, s1luz; maria s4 (enviada como `s1`, renombrada porque `maria/s1` ya existía), s1luz. 22.500 filas nuevas. Se quitaron 5 tomas porque el dedo apuntaba al lado contrario de la etiqueta (jehis s1luz toma 11; jehis s5 tomas 5, 16, 18, 20)._

**Leave-one-person-out (all data):** Left MLP 85.1% vs rules 86.2%; Right MLP 95.4% vs rules 95.1%. On Camilo (same test set as before) nothing changed: Left 77.3% (was 78.5%), Right 85.8% (was 86.0%).
_**Dejando una persona fuera (todos los datos):** izquierda MLP 85,1% vs reglas 86,2%; derecha MLP 95,4% vs reglas 95,1%. En Camilo (mismo conjunto de prueba que antes) no cambió nada: izquierda 77,3% (antes 78,5%), derecha 85,8% (antes 86,0%)._

**Lighting test:** each new session is held out. "Old data" model = trained only on the first 7 sessions; "+new data" = trained on everything except the test session.
_**Prueba de iluminación:** cada sesión nueva se deja fuera. Modelo "datos viejos" = entrenado solo con las 7 primeras sesiones; "+datos nuevos" = entrenado con todo menos la sesión de prueba._

| Hand | Test session | Old data | + new data | Rules |
|---|---|---|---|---|
| Left | jehis/s4 | 85.0% | 84.8% | 82.0% |
| Left | jehis/s5 | 72.0% | 75.1% | 73.0% |
| Left | jehis/s1luz (backlight) | 86.7% | 89.7% | 88.4% |
| Left | maria/s4 | 89.5% | 87.6% | 89.3% |
| Left | maria/s1luz (backlight) | 90.6% | 95.4% | 95.6% |
| Right | jehis/s4 | 98.5% | 98.5% | 94.7% |
| Right | jehis/s5 | 99.1% | 98.8% | 96.2% |
| Right | jehis/s1luz (backlight) | 97.2% | 96.6% | 91.4% |
| Right | maria/s4 | 99.7% | 99.6% | 98.6% |
| Right | maria/s1luz (backlight) | 92.0% | 94.6% | 95.0% |

**Conclusion:** the backlight sessions help the left-hand model in backlight (+3 to +5 points). The right hand was already at 92-99%. The weak spot is still Camilo, who has only 1 session: more of his data (or `calibrate.py`) is the next best step.
_**Conclusión:** las sesiones con contraluz ayudan al modelo de la mano izquierda en contraluz (+3 a +5 puntos). La mano derecha ya estaba en 92-99%. El punto débil sigue siendo Camilo, que solo tiene 1 sesión: más datos suyos (o `calibrate.py`) es el siguiente mejor paso._
