"""
Simulador de Teclado Virtual
Escribe texto automáticamente simulando pulsaciones de teclado.
Incluye auto-calibración para detectar y corregir caracteres problemáticos.
Soporta perfiles por máquina (local vs remota) y detección de sesión RDP.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import ctypes
from ctypes import wintypes
import json
import os
import socket

try:
    import pyautogui
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
    import pyautogui


# ═════════════════════════════════════════════════════════════
# Win32 API — Estructuras
# ═════════════════════════════════════════════════════════════

INPUT_KEYBOARD = 1
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_KEYUP = 0x0002

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [
            ("ki", KEYBDINPUT),
            ("mi", MOUSEINPUT),
            ("hi", HARDWAREINPUT),
        ]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]


# ═════════════════════════════════════════════════════════════
# Método 1: SendInput Unicode (KEYEVENTF_UNICODE)
# ═════════════════════════════════════════════════════════════

def _enviar_scan_code(scan_code):
    """Envía un único scan code (key-down + key-up) vía SendInput Unicode."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = 0
    inp.ki.wScan = scan_code & 0xFFFF
    inp.ki.dwExtraInfo = None
    inp.ki.time = 0

    inp.ki.dwFlags = KEYEVENTF_UNICODE
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

    inp.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _enviar_unicode(char):
    """Envía un carácter vía SendInput Unicode. Soporta emojis (surrogate pairs)."""
    code = ord(char)
    if code > 0xFFFF:
        # Caracteres fuera del BMP (emojis, etc.) necesitan UTF-16 surrogate pairs
        code -= 0x10000
        high_surrogate = 0xD800 + (code >> 10)
        low_surrogate = 0xDC00 + (code & 0x3FF)
        _enviar_scan_code(high_surrogate)
        _enviar_scan_code(low_surrogate)
    else:
        _enviar_scan_code(code)


# ═════════════════════════════════════════════════════════════
# Método 2: VkKeyScanW — simula teclas reales del layout actual
# ═════════════════════════════════════════════════════════════

def _key_event(vk, up=False):
    """Envía key-down o key-up para un virtual key code."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    inp.ki.dwFlags = KEYEVENTF_KEYUP if up else 0
    inp.ki.time = 0
    inp.ki.dwExtraInfo = None
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def _enviar_vkscan(char):
    """Envía un carácter simulando las teclas del layout (Shift/Ctrl/Alt según necesite)."""
    result = ctypes.windll.user32.VkKeyScanW(ord(char))
    if result == -1 or result == 0xFFFF:
        return False

    vk = result & 0xFF
    shift_state = (result >> 8) & 0xFF

    mods = []
    if shift_state & 1:
        mods.append(VK_SHIFT)
    if shift_state & 2:
        mods.append(VK_CONTROL)
    if shift_state & 4:
        mods.append(VK_MENU)

    for mod in mods:
        _key_event(mod, up=False)

    _key_event(vk, up=False)
    _key_event(vk, up=True)

    for mod in reversed(mods):
        _key_event(mod, up=True)

    return True


# ═════════════════════════════════════════════════════════════
# Detección de entorno (RDP / local)
# ═════════════════════════════════════════════════════════════

def _es_sesion_remota():
    """Detecta si estamos ejecutando dentro de una sesión de Escritorio Remoto (RDP)."""
    try:
        SM_REMOTESESSION = 0x1000
        return ctypes.windll.user32.GetSystemMetrics(SM_REMOTESESSION) != 0
    except Exception:
        return False


def _obtener_id_entorno():
    """Genera un identificador único del entorno: hostname + si es sesión remota."""
    hostname = socket.gethostname()
    remoto = "remoto" if _es_sesion_remota() else "local"
    return f"{hostname}_{remoto}"


# ═════════════════════════════════════════════════════════════
# Sistema de calibración con perfiles por entorno
# ═════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CALIBRACION_FILE = os.path.join(BASE_DIR, "calibracion.json")
PERFILES_DIR = os.path.join(BASE_DIR, "perfiles_calibracion")

# Caracteres que se prueban en la calibración
CHARS_CALIBRACION = list(dict.fromkeys(
    list("abcdefghijklmnopqrstuvwxyz")
    + list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    + list("0123456789")
    + list(" ")
    + list("{}[]()<>")
    + list("@#$%^&*~|\\/?!")
    + list("+-=_:;,.'\"`")
    + list("áéíóúÁÉÍÓÚñÑüÜ¿¡")
    # Emojis comunes (fuera del BMP, necesitan surrogate pairs)
    + list("⌨️📋🚀📖🔧🧪🛠✨⚠️⏹▶️✅⏳✍️📄")
))


def _test_char_metodo(root, entry, char, metodo_fn):
    """Envía un carácter al Entry de prueba y verifica si salió bien."""
    entry.delete(0, tk.END)
    root.update()
    time.sleep(0.03)

    metodo_fn(char)
    root.update()
    time.sleep(0.06)

    resultado = entry.get()
    entry.delete(0, tk.END)
    root.update()
    return resultado == char, resultado


def calibrar(root, estado_callback=None):
    """
    Auto-calibración: prueba cada carácter con los dos métodos,
    elige el que funciona, y guarda los resultados.
    Retorna (mapa, errores).
    """
    test_win = tk.Toplevel(root)
    test_win.title("Calibrando teclado...")
    test_win.geometry("400x100")
    test_win.attributes('-topmost', True)
    test_win.configure(bg="#1e1e2e")

    lbl = tk.Label(test_win, text="Iniciando calibración...",
                   font=("Segoe UI", 10), bg="#1e1e2e", fg="#cdd6f4")
    lbl.pack(pady=(10, 5))

    test_entry = tk.Entry(test_win, font=("Consolas", 14), width=30)
    test_entry.pack(padx=10)
    test_entry.focus_force()
    root.update()
    time.sleep(0.4)

    resultado_map = {}
    errores = []
    total = len(CHARS_CALIBRACION)

    for i, char in enumerate(CHARS_CALIBRACION):
        display = char if char != ' ' else '(espacio)'
        msg = f"[{i + 1}/{total}] Probando: '{display}'  U+{ord(char):04X}"
        lbl.config(text=msg)
        if estado_callback:
            estado_callback(msg)
        root.update()

        # --- Probar Método 1: SendInput Unicode ---
        ok1, got1 = _test_char_metodo(root, test_entry, char, _enviar_unicode)
        if ok1:
            resultado_map[char] = 'unicode'
            continue

        # --- Probar Método 2: VkKeyScanW ---
        ok2, got2 = _test_char_metodo(root, test_entry, char, _enviar_vkscan)
        if ok2:
            resultado_map[char] = 'vkscan'
            continue

        # Ninguno funcionó
        resultado_map[char] = 'unicode'  # fallback
        errores.append((char, got1, got2))

    test_win.destroy()
    root.update()

    # Guardar
    _guardar_calibracion(resultado_map)
    return resultado_map, errores


def _guardar_calibracion(mapa):
    """Guarda la calibración tanto en el archivo principal como en el perfil del entorno actual."""
    data = {char: metodo for char, metodo in mapa.items()}
    # Guardar archivo principal (compatibilidad)
    try:
        with open(CALIBRACION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    # Guardar perfil del entorno
    _guardar_perfil(data)


def _guardar_perfil(data, entorno_id=None):
    """Guarda un perfil de calibración para un entorno específico."""
    if entorno_id is None:
        entorno_id = _obtener_id_entorno()
    os.makedirs(PERFILES_DIR, exist_ok=True)
    path = os.path.join(PERFILES_DIR, f"{entorno_id}.json")
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _cargar_calibracion():
    """Carga la calibración del perfil del entorno actual. Si no existe, intenta el archivo general."""
    entorno_id = _obtener_id_entorno()
    # Intentar perfil específico del entorno
    perfil_path = os.path.join(PERFILES_DIR, f"{entorno_id}.json")
    if os.path.exists(perfil_path):
        try:
            with open(perfil_path, 'r', encoding='utf-8') as f:
                return json.load(f), entorno_id
        except Exception:
            pass
    # Fallback al archivo general
    if not os.path.exists(CALIBRACION_FILE):
        return None, entorno_id
    try:
        with open(CALIBRACION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f), entorno_id
    except Exception:
        return None, entorno_id


def _listar_perfiles():
    """Lista todos los perfiles de calibración disponibles."""
    perfiles = []
    if os.path.exists(PERFILES_DIR):
        for f in os.listdir(PERFILES_DIR):
            if f.endswith('.json'):
                perfiles.append(f.replace('.json', ''))
    return perfiles


# ═════════════════════════════════════════════════════════════
# Envío inteligente (usa calibración si existe)
# ═════════════════════════════════════════════════════════════

_metodo_por_char = {}
_metodo_forzado = None  # None = auto (calibración), 'unicode', 'vkscan'


def enviar_char(char):
    """Envía un carácter usando el método apropiado según calibración o modo forzado."""
    global _metodo_forzado

    if _metodo_forzado == 'unicode':
        _enviar_unicode(char)
        return
    elif _metodo_forzado == 'vkscan':
        if not _enviar_vkscan(char):
            _enviar_unicode(char)  # fallback si VkScan no soporta el char
        return

    # Modo auto: usar calibración
    metodo = _metodo_por_char.get(char, 'unicode')
    if metodo == 'vkscan':
        if not _enviar_vkscan(char):
            _enviar_unicode(char)
    else:
        _enviar_unicode(char)


# ═════════════════════════════════════════════════════════════
# Interfaz gráfica
# ═════════════════════════════════════════════════════════════

class TecladoSimulador:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Teclado")
        self.root.geometry("620x780")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.escribiendo = False
        self.entorno_id = _obtener_id_entorno()
        self.es_remoto = _es_sesion_remota()

        # Cargar calibración del perfil del entorno
        cal, self.entorno_id = _cargar_calibracion()
        if cal:
            _metodo_por_char.update(cal)

        self._crear_interfaz()

        # Mostrar advertencia si es sesión remota y no hay calibración del entorno
        if self.es_remoto:
            perfil_path = os.path.join(PERFILES_DIR, f"{self.entorno_id}.json")
            if not os.path.exists(perfil_path):
                self.root.after(500, self._advertir_rdp)

    def _crear_interfaz(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#89b4fa")

        # ── Título ──
        ttk.Label(self.root, text="Simulador de Teclado", style="Header.TLabel").pack(pady=(12, 2))
        ttk.Label(self.root, text="Escribe el texto, presiona Iniciar y cambia a la ventana destino.",
                  wraplength=580).pack(pady=(0, 6))

        # ── Área de texto con scrollbar ──
        frame_texto = tk.Frame(self.root, bg="#313244", bd=2, relief="groove")
        frame_texto.pack(padx=20, pady=(0, 6), fill="x")

        scrollbar = tk.Scrollbar(frame_texto)
        scrollbar.pack(side="right", fill="y")

        self.texto = tk.Text(frame_texto, wrap="word", font=("Consolas", 12),
                             bg="#313244", fg="#cdd6f4", insertbackground="#f5e0dc",
                             selectbackground="#585b70", relief="flat", padx=10, pady=10,
                             height=10, yscrollcommand=scrollbar.set)
        self.texto.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.texto.yview)

        # ── Configuración ──
        frame_config = tk.Frame(self.root, bg="#1e1e2e")
        frame_config.pack(pady=6, padx=20, fill="x")

        ttk.Label(frame_config, text="Espera antes de escribir (seg):").grid(row=0, column=0, sticky="w", pady=2)
        self.delay_var = tk.StringVar(value="3")
        tk.Spinbox(frame_config, from_=1, to=30, textvariable=self.delay_var, width=5,
                   font=("Segoe UI", 10), bg="#45475a", fg="#cdd6f4",
                   buttonbackground="#585b70").grid(row=0, column=1, padx=(8, 0), pady=2)

        ttk.Label(frame_config, text="Velocidad (seg entre teclas):").grid(row=1, column=0, sticky="w", pady=2)
        self.velocidad_var = tk.StringVar(value="0.04")
        tk.Entry(frame_config, textvariable=self.velocidad_var, width=6,
                 font=("Segoe UI", 10), bg="#45475a", fg="#cdd6f4").grid(row=1, column=1, padx=(8, 0), pady=2)

        # ── Selector de método ──
        ttk.Label(frame_config, text="Método de escritura:").grid(row=2, column=0, sticky="w", pady=2)
        self.metodo_var = tk.StringVar(value="auto")
        metodo_combo = ttk.Combobox(frame_config, textvariable=self.metodo_var,
                                     values=["auto", "unicode", "vkscan"],
                                     state="readonly", width=10,
                                     font=("Segoe UI", 10))
        metodo_combo.grid(row=2, column=1, padx=(8, 0), pady=2)
        metodo_combo.bind("<<ComboboxSelected>>", self._cambiar_metodo)

        # ── Info del entorno ──
        entorno_txt = f"{'🖥 REMOTO (RDP)' if self.es_remoto else '💻 Local'} — {self.entorno_id}"
        self.lbl_entorno = tk.Label(frame_config, text=entorno_txt,
                                     font=("Segoe UI", 9), bg="#1e1e2e",
                                     fg="#f38ba8" if self.es_remoto else "#a6e3a1")
        self.lbl_entorno.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # ── Botones ──
        frame_botones = tk.Frame(self.root, bg="#1e1e2e")
        frame_botones.pack(pady=8)

        self.btn_iniciar = tk.Button(frame_botones, text="▶  INICIAR ESCRITURA",
                                     font=("Segoe UI", 14, "bold"),
                                     bg="#a6e3a1", fg="#1e1e2e", activebackground="#94e2d5",
                                     width=22, height=2, cursor="hand2", relief="flat",
                                     command=self._iniciar)
        self.btn_iniciar.pack(pady=(0, 6))

        self.btn_detener = tk.Button(frame_botones, text="⏹  DETENER",
                                     font=("Segoe UI", 12, "bold"),
                                     bg="#f38ba8", fg="#1e1e2e", activebackground="#eba0ac",
                                     width=22, cursor="hand2", relief="flat", state="disabled",
                                     command=self._detener)
        self.btn_detener.pack(pady=(0, 6))

        self.btn_calibrar = tk.Button(frame_botones, text="🔧  CALIBRAR TECLADO",
                                      font=("Segoe UI", 10, "bold"),
                                      bg="#89b4fa", fg="#1e1e2e", activebackground="#74c7ec",
                                      width=22, cursor="hand2", relief="flat",
                                      command=self._calibrar)
        self.btn_calibrar.pack()

        # ── Estado ──
        cal, _ = _cargar_calibracion()
        perfil_existe = os.path.exists(os.path.join(PERFILES_DIR, f"{self.entorno_id}.json"))
        if cal and perfil_existe:
            n_u = sum(1 for v in cal.values() if v == 'unicode')
            n_v = sum(1 for v in cal.values() if v == 'vkscan')
            estado_init = f"Listo ({n_u}U+{n_v}V calibrados para {self.entorno_id})"
        elif cal:
            estado_init = "⚠️ Calibración de otro entorno. Recalibra para esta máquina."
        else:
            estado_init = "⚠️ Sin calibrar. Pulsa CALIBRAR TECLADO antes de usar."

        self.estado_var = tk.StringVar(value=estado_init)
        self.lbl_estado = tk.Label(self.root, textvariable=self.estado_var,
                                   font=("Segoe UI", 10, "italic"), bg="#1e1e2e", fg="#a6adc8",
                                   wraplength=580)
        self.lbl_estado.pack(pady=(8, 10))

        self.root.bind("<Escape>", lambda e: self._detener())

    # ── Cambiar método de escritura ──

    def _cambiar_metodo(self, event=None):
        global _metodo_forzado
        sel = self.metodo_var.get()
        if sel == 'auto':
            _metodo_forzado = None
            self.estado_var.set("Método: Auto (usa calibración por carácter)")
        elif sel == 'unicode':
            _metodo_forzado = 'unicode'
            self.estado_var.set("Método: Unicode forzado (funciona local, falla en RDP)")
        elif sel == 'vkscan':
            _metodo_forzado = 'vkscan'
            self.estado_var.set("Método: VkScan forzado (mejor para sesiones remotas)")

    # ── Advertencia RDP ──

    def _advertir_rdp(self):
        messagebox.showwarning(
            "Sesión remota detectada",
            "Estás conectado por Escritorio Remoto (RDP).\n\n"
            "El método Unicode suele fallar en sesiones remotas.\n\n"
            "Opciones:\n"
            "  1. Pulsa CALIBRAR TECLADO para detectar el método correcto\n"
            "  2. O cambia el método a 'vkscan' en el selector\n\n"
            f"Entorno: {self.entorno_id}"
        )

    # ── Calibración ──

    def _calibrar(self):
        self.btn_iniciar.config(state="disabled")
        self.btn_calibrar.config(state="disabled")
        self.btn_detener.config(state="disabled")
        self.estado_var.set(f"Calibrando para '{self.entorno_id}'... no toques nada.")

        def run():
            mapa, errores = calibrar(self.root, lambda msg: self.estado_var.set(msg))
            _metodo_por_char.update(mapa)

            n_unicode = sum(1 for v in mapa.values() if v == 'unicode')
            n_vkscan = sum(1 for v in mapa.values() if v == 'vkscan')

            msg = f"✅ Calibración OK [{self.entorno_id}] — {n_unicode} Unicode + {n_vkscan} VkScan"
            if errores:
                chars_err = '  '.join(f"'{c}'" for c, _, _ in errores)
                msg += f" | ⚠️ {len(errores)} sin solución: {chars_err}"

            self.estado_var.set(msg)
            self.btn_iniciar.config(state="normal")
            self.btn_calibrar.config(state="normal")

            if errores:
                detalle = "\n".join(
                    f"  '{c}' → Unicode dio '{g1}', VkScan dio '{g2}'"
                    for c, g1, g2 in errores
                )
                messagebox.showwarning(
                    "Caracteres sin solución",
                    f"Estos caracteres no se pudieron escribir correctamente:\n\n{detalle}"
                )

        self.root.after(200, run)

    # ── Escritura ──

    def _iniciar(self):
        contenido = self.texto.get("1.0", "end-1c")
        if not contenido.strip():
            messagebox.showwarning("Sin texto", "Escribe algo en el área de texto antes de iniciar.")
            return

        try:
            delay = int(self.delay_var.get())
            velocidad = float(self.velocidad_var.get())
        except ValueError:
            messagebox.showerror("Error", "Los valores de espera y velocidad deben ser numéricos.")
            return

        self.escribiendo = True
        self.btn_iniciar.config(state="disabled")
        self.btn_detener.config(state="normal")
        self.btn_calibrar.config(state="disabled")

        hilo = threading.Thread(target=self._escribir,
                                args=(contenido, delay, velocidad),
                                daemon=True)
        hilo.start()

    def _escribir(self, texto, delay, velocidad):
        for i in range(delay, 0, -1):
            if not self.escribiendo:
                self._restablecer("Cancelado.")
                return
            self.estado_var.set(f"⏳ Escribiendo en {i} segundos... ¡Cambia a la ventana destino!")
            time.sleep(1)

        self.estado_var.set("✍️ Escribiendo...")
        pyautogui.FAILSAFE = True

        for char in texto:
            if not self.escribiendo:
                self._restablecer("Detenido por el usuario.")
                return

            if char == '\n':
                pyautogui.press('enter')
            elif char == '\t':
                enviar_char('\t')
            else:
                enviar_char(char)

            time.sleep(velocidad)

        self._restablecer("✅ ¡Texto escrito correctamente!")

    def _detener(self):
        self.escribiendo = False

    def _restablecer(self, mensaje):
        self.estado_var.set(mensaje)
        self.btn_iniciar.config(state="normal")
        self.btn_detener.config(state="disabled")
        self.btn_calibrar.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = TecladoSimulador(root)
    root.mainloop()
