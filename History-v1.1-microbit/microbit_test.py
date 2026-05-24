import tkinter as tk
from tkinter import ttk
import threading
import serial
import serial.tools.list_ports
import os
import sys

def get_external_path(file_name):
    """ Връща пътя до файл, който се намира ВЪН до .exe-то """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, file_name)

# ── Намиране на портове ──────────────────────────────────────
def get_ports():
    return serial.tools.list_ports.comports()

def refresh_ports():
    ports = get_ports()
    combo['values'] = [f"{p.device} — {p.description}" for p in ports]
    if ports:
        combo.current(0)
    lbl_status.config(text=f"Намерени {len(ports)} порта", fg="gray")

# ── Свързване / Разкачане / Запазване ────────────────────────
ser = None
listener_running = False

def connect():
    global ser, listener_running
    selection = combo.get()
    if not selection:
        lbl_status.config(text="Избери порт!", fg="red")
        return

    port = selection.split(" — ")[0]
    baud = int(baud_var.get())

    try:
        ser = serial.Serial(port, baud, timeout=1)
        listener_running = True
        threading.Thread(target=listen, daemon=True).start()
        btn_connect.config(state="disabled")
        btn_disconnect.config(state="normal")
        lbl_status.config(text=f"Свързан на {port} @ {baud}", fg="green")
        log(f"── Свързан на {port} @ {baud} baud ──")
    except Exception as e:
        lbl_status.config(text=f"Грешка: {e}", fg="red")

def disconnect():
    global ser, listener_running
    listener_running = False
    if ser and ser.is_open:
        ser.close()
    btn_connect.config(state="normal")
    btn_disconnect.config(state="disabled")
    lbl_status.config(text="Разкачен", fg="gray")
    log("── Разкачен ──")

def save_for_game():
    selection = combo.get()
    if not selection:
        lbl_status.config(text="Избери порт!", fg="red")
        return
    
    # Задължително разкачаме порта, за да е свободен за главната игра
    disconnect()
    
    port = selection.split(" — ")[0]
    try:
        config_path = get_external_path("microbit_port.txt")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(port)
        lbl_status.config(text=f"Успешно: {port} е запазен!", fg="green")
        log(f"── Портът {port} е записан за играта! ──\nМожеш да затвориш този прозорец и да обновиш в играта.")
    except Exception as e:
        lbl_status.config(text=f"Грешка при запис: {e}", fg="red")
        log(f"[ГРЕШКА] {e}")

# ── Слушане на серийния порт ─────────────────────────────────
def listen():
    global ser, listener_running
    while listener_running and ser and ser.is_open:
        try:
            raw = ser.readline()
            if raw:
                try:
                    text = raw.decode("utf-8").strip()
                except UnicodeDecodeError:
                    text = raw.hex()
                root.after(0, lambda t=text: log(f">>> {t}"))
        except Exception as e:
            if listener_running:
                root.after(0, lambda e=e: log(f"[ГРЕШКА] {e}"))
            break

# ── Лог ─────────────────────────────────────────────────────
def log(msg):
    txt.config(state="normal")
    txt.insert("end", msg + "\n")
    txt.see("end")
    txt.config(state="disabled")

def clear_log():
    txt.config(state="normal")
    txt.delete("1.0", "end")
    txt.config(state="disabled")

# ── GUI ──────────────────────────────────────────────────────
root = tk.Tk()
root.title("Micro:bit Тест — Сериен монитор")
# Увеличих малко ширината, за да се събере новият бутон
root.geometry("820x500")
root.resizable(False, False)

tk.Label(root, text="Micro:bit Сериен Монитор", font=("Arial", 14, "bold")).pack(pady=(12, 4))

frame_top = tk.Frame(root)
frame_top.pack(fill="x", padx=15, pady=5)

tk.Label(frame_top, text="Порт:").grid(row=0, column=0, sticky="w")
combo = ttk.Combobox(frame_top, width=38, state="readonly")
combo.grid(row=0, column=1, padx=5)

tk.Label(frame_top, text="Baud:").grid(row=0, column=2, sticky="w", padx=(10,0))
baud_var = tk.StringVar(value="115200")
baud_combo = ttk.Combobox(frame_top, textvariable=baud_var,
                              values=["9600", "19200", "38400", "57600", "115200"],
                              width=8, state="readonly")
baud_combo.grid(row=0, column=3, padx=5)

frame_btns = tk.Frame(root)
frame_btns.pack(pady=6)

tk.Button(frame_btns, text="🔄 Обнови портове", command=refresh_ports,
          width=15, bg="#607D8B", fg="white").pack(side="left", padx=4)

btn_connect = tk.Button(frame_btns, text="▶ Свържи", command=connect,
                        width=12, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
btn_connect.pack(side="left", padx=4)

btn_disconnect = tk.Button(frame_btns, text="■ Разкачи", command=disconnect,
                            width=12, bg="#f44336", fg="white", state="disabled")
btn_disconnect.pack(side="left", padx=4)

tk.Button(frame_btns, text="🗑 Изчисти", command=clear_log,
          width=10, bg="#FF9800", fg="white").pack(side="left", padx=4)

# Новият бутон за запис
btn_use = tk.Button(frame_btns, text="✔ Използвай в играта", command=save_for_game,
                    width=20, bg="#2196F3", fg="white", font=("Arial", 10, "bold"))
btn_use.pack(side="left", padx=4)

lbl_status = tk.Label(root, text="Не е свързан", fg="gray", font=("Arial", 10, "italic"))
lbl_status.pack()

frame_log = tk.Frame(root, bd=2, relief="sunken")
frame_log.pack(fill="both", expand=True, padx=15, pady=(5, 15))

txt = tk.Text(frame_log, font=("Consolas", 11), bg="#1e1e1e", fg="#00ff99",
              state="disabled", wrap="word")
scrollbar = tk.Scrollbar(frame_log, command=txt.yview)
txt.config(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
txt.pack(fill="both", expand=True)

refresh_ports()
log("Избери COM порт и натисни 'Свържи'.")
log("За да го ползваш в главната игра, натисни '✔ Използвай в играта'.")
log("─" * 45)

root.mainloop()