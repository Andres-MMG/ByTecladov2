# ⌨️ Simulador de Teclado Virtual

Programa con interfaz gráfica que simula pulsaciones de teclado. Escribe un texto en la app, presiona iniciar y el programa lo "teclea" automáticamente en cualquier ventana que elijas.

---

## 📋 Requisitos

- **Python 3.7+** instalado ([Descargar Python](https://www.python.org/downloads/))
- Sistema operativo: **Windows**

## 🚀 Instalación

1. **Clonar o descargar** este repositorio:

   ```bash
   git clone <url-del-repositorio>
   cd ByTeclado
   ```

2. **Instalar dependencias**:

   ```bash
   pip install pyautogui
   ```

   > Si `pip` no funciona, prueba con `py -m pip install pyautogui`

## ▶️ Cómo ejecutar

```bash
py teclado_virtual.py
```

## 📖 Instrucciones de uso

1. **Abrir la aplicación** ejecutando el comando anterior.
2. **Calibrar el teclado** (solo la primera vez o si cambias de entorno):
   - Pulsa el botón azul **"CALIBRAR TECLADO"**.
   - El programa probará cada carácter automáticamente y detectará cuáles fallan.
   - Para los que fallen, probará un método alternativo y guardará la configuración.
   - La calibración se guarda en `calibracion.json` y se reutiliza en futuras ejecuciones.
3. **Escribir el texto** que deseas que se teclee automáticamente en el área de texto.
4. **Configurar** (opcional):
   | Opción | Default | Descripción |
   |--------|---------|-------------|
   | Espera | 3 seg | Cuenta regresiva antes de empezar. Te da tiempo para cambiar a la ventana destino. |
   | Velocidad | 0.04 seg | Pausa entre cada pulsación de tecla. Menor = más rápido. |
5. **Presionar el botón verde "INICIAR ESCRITURA"**.
6. **Cambiar rápidamente** a la ventana donde quieres que se escriba el texto (Notepad, navegador, chat, etc.).
7. Esperar la cuenta regresiva. El programa escribirá carácter por carácter simulando el teclado.

## 🔧 Calibración

El sistema de calibración detecta automáticamente qué caracteres se escriben mal y elige el mejor método para cada uno:

- **Método 1 — SendInput Unicode**: Envía el carácter Unicode directamente. Funciona en la mayoría de apps.
- **Método 2 — VkKeyScanW**: Simula las teclas reales del layout actual (Shift, AltGr, etc.). Útil cuando Unicode falla.

Los resultados se guardan en `calibracion.json`. Si cambias de máquina, idioma del teclado, o entorno (local vs. remoto), recalibra.

## ⏹️ Cómo detener

- Presionar el **botón rojo "DETENER"** en la app.
- Presionar la tecla **Escape** en el teclado.
- **Mover el ratón a la esquina superior izquierda** de la pantalla (failsafe de seguridad).

## ✨ Características

- Interfaz gráfica oscura y moderna.
- **Auto-calibración** para detectar y corregir caracteres problemáticos.
- Dos métodos de escritura con selección automática por carácter.
- No depende del portapapeles (funciona en escritorios remotos sin clipboard compartido).
- Cuenta regresiva configurable para cambiar de ventana.
- Velocidad de escritura ajustable.
- Soporte para **caracteres especiales** (ñ, tildes, acentos, {}, [], @, #, etc.).
- Soporte para saltos de línea y tabulaciones.
- Mecanismo de seguridad (failsafe) para abortar en cualquier momento.

