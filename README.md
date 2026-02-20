# ⌨️ Simulador de Teclado Virtual

Programa con interfaz gráfica que simula pulsaciones de teclado. Escribe un texto en la app, presiona iniciar y el programa lo "teclea" automáticamente en cualquier ventana que elijas. Funciona tanto en sesiones locales como en escritorios remotos (RDP).

---

## 📋 Requisitos

- **Python 3.7+** instalado ([Descargar Python](https://www.python.org/downloads/))
- Sistema operativo: **Windows**

## 🚀 Instalación

1. **Clonar o descargar** este repositorio:

   ```bash
   git clone <url-del-repositorio>
   cd ByTecladov2
   ```

2. **Instalar dependencias**:

   ```bash
   pip install pyautogui
   ```

   > Si `pip` no funciona, prueba con `py -m pip install pyautogui`
   >
   > Si no tienes `pyautogui` instalado, el programa lo instala automáticamente al ejecutarse.

## ▶️ Cómo ejecutar

```bash
py teclado_virtual.py
```

## 📖 Instrucciones de uso

1. **Abrir la aplicación** ejecutando el comando anterior.
2. **Calibrar el teclado** (solo la primera vez o si cambias de entorno):
   - Pulsa el botón azul **"CALIBRAR TECLADO"**.
   - El programa probará cada carácter automáticamente con los tres métodos de escritura.
   - Para cada carácter, selecciona el primer método que funcione correctamente.
   - La calibración se guarda en `calibracion.json` y en un perfil específico por entorno en `perfiles_calibracion/`.
3. **Escribir el texto** que deseas que se teclee automáticamente en el área de texto.
4. **Configurar** (opcional):
   | Opción | Default | Descripción |
   |--------|---------|-------------|
   | Espera | 3 seg | Cuenta regresiva antes de empezar. Te da tiempo para cambiar a la ventana destino. |
   | Velocidad | 0.04 seg | Pausa entre cada pulsación de tecla. Menor = más rápido. |
   | Método | auto (local) / vkscan (RDP) | Método de escritura: auto, unicode, vkscan o clipboard. |
5. **Presionar el botón verde "INICIAR ESCRITURA"**.
6. **Cambiar rápidamente** a la ventana donde quieres que se escriba el texto (Notepad, navegador, chat, etc.).
7. Esperar la cuenta regresiva. El programa escribirá carácter por carácter simulando el teclado.

## 🔧 Calibración

El sistema de calibración detecta automáticamente qué caracteres se escriben mal y elige el mejor método para cada uno:

- **Método 1 — SendInput Unicode**: Envía el carácter Unicode directamente. Funciona en la mayoría de apps locales. Soporta emojis y caracteres fuera del BMP (surrogate pairs).
- **Método 2 — VkKeyScanW**: Simula las teclas reales del layout actual (Shift, AltGr, etc.). Ideal para sesiones de Escritorio Remoto (RDP).
- **Método 3 — Clipboard**: Copia el carácter al portapapeles y pega con Ctrl+V. Funciona siempre como último recurso, pero es más lento.

### Perfiles por entorno

La calibración soporta **perfiles por máquina y tipo de sesión** (local vs. remoto). Al calibrar, se genera un perfil con el formato `hostname_local.json` o `hostname_remoto.json` dentro de la carpeta `perfiles_calibracion/`. De esta forma, si usas el programa tanto en local como por RDP, cada entorno mantiene su propia calibración sin interferir con la otra.

Los resultados también se guardan en `calibracion.json` por compatibilidad. Si cambias de máquina, idioma del teclado, o entorno (local vs. remoto), recalibra.

## 🖥️ Soporte para Escritorio Remoto (RDP)

El programa detecta automáticamente si se está ejecutando dentro de una sesión de Escritorio Remoto:

- Muestra una **advertencia al iniciar** si no existe una calibración para el entorno remoto actual.
- Cambia el método de escritura por defecto a **vkscan**, que suele funcionar mejor en RDP.
- La barra de estado indica si es sesión local o remota y el identificador del entorno.

## ⏹️ Cómo detener

- Presionar el **botón rojo "DETENER"** en la app.
- Presionar la tecla **Escape** en el teclado.
- **Mover el ratón a la esquina superior izquierda** de la pantalla (failsafe de seguridad).

## ✨ Características

- Interfaz gráfica oscura y moderna (tema Catppuccin).
- **Auto-calibración** para detectar y corregir caracteres problemáticos.
- **Tres métodos de escritura** (Unicode, VkScan, Clipboard) con selección automática o manual.
- **Perfiles de calibración por entorno** (local vs. RDP) con detección automática.
- Detección automática de sesiones de Escritorio Remoto (RDP).
- Soporte para **emojis** y caracteres fuera del BMP (UTF-16 surrogate pairs).
- Selector de método de escritura en la interfaz (auto, unicode, vkscan, clipboard).
- Cuenta regresiva configurable para cambiar de ventana.
- Velocidad de escritura ajustable.
- Soporte para **caracteres especiales** (ñ, tildes, acentos, {}, [], @, #, etc.).
- Soporte para saltos de línea y tabulaciones.
- Mecanismo de seguridad (failsafe) para abortar en cualquier momento.
- Instalación automática de `pyautogui` si no está presente.

## 📁 Estructura del proyecto

```
ByTecladov2/
├── teclado_virtual.py        # Programa principal
├── calibracion.json           # Calibración general (compatibilidad)
├── perfiles_calibracion/      # Perfiles de calibración por entorno
│   ├── PC-LOCAL_local.json
│   └── PC-REMOTO_remoto.json
└── README.md
```

