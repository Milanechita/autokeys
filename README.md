# Piano Autoplayer

Autoplayer de piano para Windows que lee partituras en formato **Virtual Piano**
(el que usan los juegos de piano de Roblox) y las toca enviando las teclas al juego.

Interfaz simple: pegás la partitura, ajustás el tempo y presionás F5.

![formato](songs/ejemplo.txt)

## Características

- Lee formato Virtual Piano: acordes `[abc]`, notas sueltas, notas pegadas que subdividen el beat, y símbolos con Shift (`$ % ^`...).
- Envío de teclas por `SendInput` con **scancodes físicos** — funciona con Roblox y con cualquier layout de teclado (US, ES-LA, etc).
- Panel de ajustes con sliders: tempo (modificable **en vivo**), pulsación, pausa por línea, humanización, transposición y cuenta atrás.
- Hotkeys globales: **F5** tocar · **F6** detener · **F7** pausa · **F8/F9** subir/bajar tempo. Funcionan desde adentro del juego.
- Biblioteca de canciones guardadas con nombre.
- Guardado de configuración en `autoplayer_config.json`.
- Contador de notas en tiempo real mientras editás la partitura.

## Uso rápido

1. Instalá [Python 3.8+](https://python.org) (marcá *Add Python to PATH* en el instalador).
2. Corré:
   ```
   python src/autoplayer.py
   ```
3. Pegá la partitura, ajustá el tempo, apretá **F5**, y hacé alt-tab a Roblox antes de que termine la cuenta atrás.

## Generar el .exe

Doble click en `build/COMPILAR_EXE.bat`. Instala PyInstaller solo, compila, y deja
el ejecutable autónomo en `dist/PianoAutoplayer.exe`. Ese archivo funciona sin Python instalado.

> Windows Defender puede marcar el .exe como falso positivo (típico de PyInstaller `--onefile`).
> Agregá una excepción para la carpeta, o compilá sin `--onefile`.

## Formato de partitura

| Sintaxis        | Significado                                  |
|-----------------|----------------------------------------------|
| `u`             | una nota                                     |
| `[uf]`          | acorde: `u` y `f` juntas                     |
| `u u u`         | tres notas, una por beat                     |
| `uuuu`          | cuatro notas repartidas en un solo beat      |
| `$` `%` `A`     | tecla con Shift                              |
| `u---`          | nota alargada (cada `-` suma un beat)        |
| `-` (suelto)    | pausa de un beat                             |
| línea en blanco | pausa                                        |
| `\|`            | separador visual, se ignora                  |

## Ajustes

- **Tempo (BPM)** — velocidad general. Se puede cambiar mientras suena.
- **Pulsación (ms)** — cuánto se mantiene cada tecla apretada.
- **Pausa por línea** — silencio entre líneas, en beats.
- **Humanizar (ms)** — desincroniza cada nota al azar para que no suene robótico.
- **Transponer** — mueve todo en semitonos; descarta notas fuera del rango.
- **Cuenta atrás (s)** — margen para hacer alt-tab antes de arrancar.

**Auto-Tempo** — botón junto al BPM que analiza la partitura pegada y, si la parte
más rápida quedaría demasiado comprimida para que el juego registre cada tecla,
baja el tempo a un valor seguro (nunca lo sube: el formato no lleva un tempo
"real" para adivinar). También muestra la duración estimada de la canción.

**Restablecer ajustes** — botón que devuelve todos los sliders del panel a sus
valores por defecto de fábrica.

## Aviso

Herramienta educativa. Algunos servidores de Roblox tienen detección de macros;
usar la humanización reduce la regularidad perfecta de los inputs. Usalo bajo tu
propia responsabilidad y respetando las reglas de cada juego.

## Licencia

MIT — ver [LICENSE](LICENSE).
