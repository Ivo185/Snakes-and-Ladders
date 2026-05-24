import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import os

FILE_NAME = "Въпроси.md"
DEFAULT_TIMER = 60

def load_all_questions():
    listbox.delete(0, tk.END)
    if not os.path.exists(FILE_NAME):
        return
    try:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    listbox.insert(tk.END, line.strip())
    except Exception as e:
        messagebox.showerror("Грешка", f"Неуспешно зареждане: {e}")

def add_question():
    diff  = combo_diff.get()
    q     = entry_q.get().strip()
    a     = entry_a.get().strip()
    timer = entry_timer.get().strip()

    if not q or not a:
        messagebox.showwarning("Внимание", "Попълнете въпроса и отговора!")
        return
    if not timer.isdigit() or int(timer) < 5:
        messagebox.showwarning("Внимание", "Таймерът трябва да е число >= 5!")
        return

    prefix = ""
    if os.path.exists(FILE_NAME) and os.path.getsize(FILE_NAME) > 0:
        with open(FILE_NAME, "r", encoding="utf-8") as f_check:
            content = f_check.read()
            if not content.endswith("\n"):
                prefix = "\n"

    line = f"{prefix}{diff} | {q} | {a} | {timer}\n"

    try:
        with open(FILE_NAME, "a", encoding="utf-8") as f:
            f.write(line)
        entry_q.delete(0, tk.END)
        entry_a.delete(0, tk.END)
        entry_timer.delete(0, tk.END)
        entry_timer.insert(0, str(DEFAULT_TIMER))
        load_all_questions()
        messagebox.showinfo("Успех", f"Въпросът е добавен! Ниво: {diff}, Таймер: {timer}s")
    except Exception as e:
        messagebox.showerror("Грешка", f"Грешка при запис: {e}")

def delete_selected():
    selection = listbox.curselection()
    if not selection:
        messagebox.showwarning("Внимание", "Изберете въпрос от списъка!")
        return
    if messagebox.askyesno("Потвърждение", "Сигурни ли сте?"):
        idx = selection[0]
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            lines = f.readlines()
        del lines[idx]
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.writelines(lines)
        load_all_questions()

def edit_selected():
    selection = listbox.curselection()
    if not selection:
        messagebox.showwarning("Внимание", "Изберете ред за редактиране!")
        return
    idx = selection[0]
    current_line = listbox.get(idx)
    new_val = simpledialog.askstring("Редактиране",
                                     "Формат: Трудност | Въпрос | Отговор | Секунди",
                                     initialvalue=current_line)
    if new_val and new_val.count("|") == 3:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            lines = f.readlines()
        lines[idx] = new_val.strip() + "\n"
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.writelines(lines)
        load_all_questions()
    elif new_val:
        messagebox.showwarning("Грешка", "Трябват три вертикални черти '|'! (Трудност | Въпрос | Отговор | Секунди)")

def set_all_timers():
    """Задава един таймер за всички въпроси."""
    val = simpledialog.askstring("Задай таймер", "Въведи секунди за ВСИЧКИ въпроси:", initialvalue="60")
    if val and val.isdigit() and int(val) >= 5:
        with open(FILE_NAME, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        for line in lines:
            if "|" in line:
                parts = [p.strip() for p in line.rstrip("\n").split("|")]
                if len(parts) == 3:
                    parts.append(val)
                elif len(parts) >= 4:
                    parts[3] = val
                new_lines.append(" | ".join(parts) + "\n")
            else:
                new_lines.append(line)
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        load_all_questions()
        messagebox.showinfo("Готово", f"Всички въпроси вече имат таймер {val}s")
    elif val:
        messagebox.showwarning("Грешка", "Въведи число >= 5!")

root = tk.Tk()
root.title("Редактор на въпроси")
root.geometry("800x600")

frame_input = tk.LabelFrame(root, text=" Добавяне на нов въпрос ", padx=10, pady=10)
frame_input.pack(fill="x", padx=15, pady=10)

tk.Label(frame_input, text="Въпрос:").grid(row=0, column=0, sticky="w")
entry_q = tk.Entry(frame_input, width=70)
entry_q.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

tk.Label(frame_input, text="Отговор:").grid(row=1, column=0, sticky="w")
entry_a = tk.Entry(frame_input, width=70)
entry_a.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

tk.Label(frame_input, text="Трудност:").grid(row=2, column=0, sticky="w")
combo_diff = ttk.Combobox(frame_input, values=["Лесно", "Трудно"], state="readonly", width=15)
combo_diff.set("Лесно")
combo_diff.grid(row=2, column=1, sticky="w", padx=5, pady=5)

tk.Label(frame_input, text="Таймер (сек):").grid(row=3, column=0, sticky="w")
entry_timer = tk.Entry(frame_input, width=8)
entry_timer.insert(0, str(DEFAULT_TIMER))
entry_timer.grid(row=3, column=1, sticky="w", padx=5, pady=5)
tk.Label(frame_input, text="секунди (минимум 5)", fg="gray").grid(row=3, column=1, sticky="e", padx=5)

btn_add = tk.Button(frame_input, text="ДОБАВИ ВЪПРОС", command=add_question,
                    bg="#4CAF50", fg="white", font=("Arial", 9, "bold"))
btn_add.grid(row=3, column=2, sticky="e", padx=5)

frame_list = tk.Frame(root)
frame_list.pack(fill="both", expand=True, padx=15)

tk.Label(frame_list, text="Списък (Трудност | Въпрос | Отговор | Секунди):", font=("Arial", 10, "bold")).pack(anchor="w")
listbox = tk.Listbox(frame_list, width=100, height=15, font=("Consolas", 9))
listbox.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(frame_list)
scrollbar.pack(side="right", fill="y")
listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=listbox.yview)

frame_btns = tk.Frame(root, pady=10)
frame_btns.pack()

tk.Button(frame_btns, text="РЕДАКТИРАЙ ИЗБРАНИЯ", command=edit_selected, bg="#2196F3", fg="white", width=22).pack(side="left", padx=8)
tk.Button(frame_btns, text="ИЗТРИЙ ИЗБРАНИЯ",     command=delete_selected, bg="#f44336", fg="white", width=22).pack(side="left", padx=8)
tk.Button(frame_btns, text="ЗАДАЙ ТАЙМЕР ЗА ВСИЧКИ", command=set_all_timers, bg="#FF9800", fg="white", width=24).pack(side="left", padx=8)

load_all_questions()
root.mainloop()