# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [Sin publicar]
### Añadido
- Botón "Auto-Tempo" junto al slider de BPM: analiza la partitura pegada y, si la
  sección más rápida quedaría por debajo de un umbral confiable para el envío de
  teclas, baja el tempo automáticamente a un valor seguro. Nunca lo sube — el
  formato Virtual Piano no lleva tempo real, así que no hay forma de "adivinar"
  uno más rápido, solo de evitar uno demasiado denso para que el juego lo reciba
  bien. Muestra también la duración estimada resultante.
- Botón "Restablecer ajustes": vuelve todos los sliders del panel (tempo,
  pulsación, pausa por línea, humanización, transposición, cuenta atrás) a sus
  valores por defecto de fábrica, sin tocar el archivo de configuración
  guardado hasta que apretás "Guardar ajustes".

## [0.3.0] - 2026-08-17
### Añadido
- Control de tempo en vivo: botones +/- junto al BPM, flechas ↑/↓ con la ventana enfocada, y hotkeys globales F8 (subir) / F9 (bajar), en pasos de 5.
- Biblioteca de canciones: guardar la partitura actual con nombre, cargarla desde un desplegable y borrarla. Se guarda en `autoplayer_songs.json`.
- Soporte de notas con duración: `-` alarga la nota o acorde previo un beat (`u---` dura 4), y un `-` suelto es una pausa de un beat.

## [0.2.1] - 2026-08-16
### Corregido
- Bug crítico: la estructura `INPUT` medía 32 bytes en vez de 40 en Windows 64-bit, así que `SendInput` rechazaba todas las teclas en silencio y no escribía nada en ningún lado. Ahora mide 40 correctamente.
### Añadido
- Verificación del tamaño de `INPUT` al arrancar.
- Aviso en la barra de estado si `SendInput` es rechazado (sugiere ejecutar como administrador).

## [0.2.0] - 2026-08-16
### Añadido
- Panel de ajustes con sliders: tempo, pulsación, pausa por línea, humanización, transposición y cuenta atrás.
- Tempo modificable en vivo mientras se reproduce.
- Transposición cromática en semitonos (descarta notas fuera de rango).
- Humanización: jitter aleatorio por nota.
- Botones Pegar / Limpiar / Abrir .txt y contador de notas en tiempo real.
- Guardado y carga de configuración (`autoplayer_config.json`).

## [0.1.0] - 2026-08-16
### Añadido
- Parser del formato Virtual Piano (acordes, notas pegadas, símbolos con Shift).
- Envío de teclas por SendInput con scancodes físicos.
- Interfaz tkinter básica con tempo, pulsación, pausa y cuenta atrás.
- Hotkeys globales F5 / F6 / F7.
- Script de compilación a .exe con PyInstaller.
