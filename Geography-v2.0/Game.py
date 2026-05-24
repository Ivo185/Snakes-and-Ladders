import tkinter as tk
from tkinter import simpledialog, messagebox
import random
import time
import os
import sys
import threading
import subprocess


try:
    from PIL import Image, ImageTk, ImageFilter, ImageEnhance
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False


try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_external_path(file_name):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, file_name)


def load_questions_from_file(file_name):
    all_q = []
    full_path = get_external_path(file_name)
    if not os.path.exists(full_path):
        return [{"q": f"Липсва файл '{file_name}'!", "a": "error", "diff": "Лесно", "timer": 60}]
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                if "|" in line:
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) >= 4:
                        diff   = parts[0]
                        q_text = parts[1]
                        ans    = parts[2]
                        try:
                            timer = int(parts[3])
                        except ValueError:
                            timer = 60
                        all_q.append({"diff": diff, "q": q_text, "a": ans, "timer": timer})
                    elif len(parts) == 3:
                        all_q.append({"diff": parts[0], "q": parts[1], "a": parts[2], "timer": 60})
                    elif len(parts) == 2:
                        all_q.append({"diff": "Лесно", "q": parts[0], "a": parts[1], "timer": 60})
    except Exception as e:
        return [{"q": f"Грешка: {e}", "a": "error", "diff": "Лесно", "timer": 60}]
    return all_q if all_q else [{"q": "Файлът е празен!", "a": "error", "diff": "Лесно", "timer": 60}]


ALL_QUESTIONS = load_questions_from_file("Въпроси.md")
LADDERS = {8: 30, 18: 56, 33: 52, 60: 79, 68: 87, 76: 97}
SNAKES = {26: 5, 59: 21, 66: 47, 72: 50, 99: 63}
SPECIAL_SQUARES = list(LADDERS.keys()) + list(SNAKES.keys())


class FullscreenGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Змии, Стълби и Знание")
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.exit_game())
        
        self.width = self.root.winfo_screenwidth()
        self.height = self.root.winfo_screenheight()
        self.scale = self.height / 1080
        
        if PYGAME_AVAILABLE:
            try: pygame.mixer.init()
            except: pass
            
        self.players_count = 2
        self.current_player = 1
        self.positions = {}
        self.active_questions = []
        self.is_moving = False
        
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        self.load_resources()
        self.show_scene_start()


    def load_image(self, path, w, h):
        final_path = resource_path(path)
        try:
            if HAS_PILLOW:
                img = Image.open(final_path)
                img = img.resize((w, h), Image.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
            else:
                return tk.PhotoImage(file=final_path)
        except: return None


    def prepare_button_anims(self, path, width, height):
        final_path = resource_path(path)
        if not HAS_PILLOW or not os.path.exists(final_path):
            img = self.load_image(path, width, height)
            return {'normal': img, 'hover_frames': [img], 'click': img}
        
        orig = Image.open(final_path).convert("RGBA")
        orig = orig.resize((width, height), Image.Resampling.LANCZOS)
        
        frames = []
        for scale in [0.98, 0.96, 0.94, 0.92, 0.90, 0.88]:
            nw, nh = int(width * scale), int(height * scale)
            frame = orig.resize((nw, nh), Image.Resampling.LANCZOS)
            frames.append(ImageTk.PhotoImage(frame))
            
        click_img = orig.resize((int(width * 0.88), int(height * 0.88)), Image.Resampling.LANCZOS)
        enhancer = ImageEnhance.Brightness(click_img)
        click_img = enhancer.enhance(0.7)
        
        return {'normal': ImageTk.PhotoImage(orig), 'hover_frames': frames, 'click': ImageTk.PhotoImage(click_img)}


    def _animate_btn(self, tag, anim_data, frame_idx, forward):
        if not hasattr(self, 'btn_anim_jobs'):
            self.btn_anim_jobs = {}
        if tag in self.btn_anim_jobs:
            self.root.after_cancel(self.btn_anim_jobs[tag])
            
        frames = anim_data['hover_frames']
        delay = 15
        
        if forward and frame_idx < len(frames):
            self.canvas.itemconfig(tag, image=frames[frame_idx])
            self.btn_anim_jobs[tag] = self.root.after(delay, lambda: self._animate_btn(tag, anim_data, frame_idx + 1, forward))
        elif not forward and frame_idx >= 0:
            self.canvas.itemconfig(tag, image=frames[frame_idx])
            self.btn_anim_jobs[tag] = self.root.after(delay, lambda: self._animate_btn(tag, anim_data, frame_idx - 1, forward))
        elif not forward and frame_idx < 0:
            self.canvas.itemconfig(tag, image=anim_data['normal'])


    def bind_animated_button(self, tag, anim_data, command):
        def on_enter(e):
            self.canvas.config(cursor="hand2")
            self._animate_btn(tag, anim_data, 0, forward=True)
        def on_leave(e):
            self.canvas.config(cursor="")
            self._animate_btn(tag, anim_data, len(anim_data['hover_frames']) - 1, forward=False)
        def on_click(e):
            self.canvas.itemconfig(tag, image=anim_data['click'])
            self.canvas.move(tag, 3, 3)
        def on_release(e):
            self.canvas.move(tag, -3, -3)
            self.canvas.itemconfig(tag, image=anim_data['hover_frames'][-1])
            command() 
            
        self.canvas.tag_bind(tag, "<Enter>", on_enter)
        self.canvas.tag_bind(tag, "<Leave>", on_leave)
        self.canvas.tag_bind(tag, "<Button-1>", on_click)
        self.canvas.tag_bind(tag, "<ButtonRelease-1>", on_release)


    def load_resources(self):
        self.images = {}
        self.btn_anims = {}
        bg_folder = "img/backrounds/"
        
        self.images['bg_start'] = self.load_image(f"{bg_folder}Start.png", self.width, self.height)
        self.images['bg_rules'] = self.load_image(f"{bg_folder}Правила.png", self.width, self.height)
        self.images['bg_players'] = self.load_image(f"{bg_folder}Players numbers.png", self.width, self.height)
        self.images['bg_diff'] = self.load_image(f"{bg_folder}Избери трудност.png", self.width, self.height)
        self.images['bg_correct'] = self.load_image(f"{bg_folder}Правилен отговор.png", self.width, self.height)
        self.images['bg_wrong'] = self.load_image(f"{bg_folder}Грешен отговор.png", self.width, self.height)
        self.images['bg_win'] = self.load_image(f"{bg_folder}win.png", self.width, self.height)
        self.images['bg_field'] = self.load_image(f"{bg_folder}playing field.png", self.height, self.height)
        self.images['bg_table'] = self.load_image(f"{bg_folder}table.png", self.width, self.height)
        
        self.btn_anims['start'] = self.prepare_button_anims("img/buttons/start.png", int(400 * self.scale), int(180 * self.scale))
        self.btn_anims['rules'] = self.prepare_button_anims("img/buttons/pravila.png", int(400 * self.scale), int(160 * self.scale))
        self.btn_anims['lesno'] = self.prepare_button_anims("img/buttons/lesno.png", int(350 * self.scale), int(150 * self.scale))
        self.btn_anims['trydno'] = self.prepare_button_anims("img/buttons/trydno.png", int(350 * self.scale), int(150 * self.scale))
        self.btn_anims['vsiqko'] = self.prepare_button_anims("img/buttons/vsiqko.png", int(500 * self.scale), int(200 * self.scale))
        self.btn_anims['house'] = self.prepare_button_anims("img/house/house.png", int(218 * self.scale), int(300 * self.scale))
        self.btn_anims['house_small'] = self.prepare_button_anims("img/house/house.png", int(130 * self.scale), int(180 * self.scale))
        
        for i in range(2, 7):
            self.btn_anims[f'{i}p'] = self.prepare_button_anims(f"img/buttons/{i} players.png", int(553 * self.scale), int(160 * self.scale))
            
        self.zar_images = {}
        self.zar_images['натисни'] = self.load_image("img/zar/натисни.png", int(230 * self.scale), int(210 * self.scale))
        for i in range(1, 7):
            self.zar_images[i] = self.load_image(f"img/zar/{i}.png", int(258 * self.scale), int(296 * self.scale))
            
        self.player_images = []
        for i in range(1, 7):
            p_path = (resource_path(f"img/players/p{i}.png"))
            try:
                if HAS_PILLOW:
                    with Image.open(p_path) as temp_img:
                        orig_w, orig_h = temp_img.size
                    new_w = int(80 * self.scale)
                    new_h = int((orig_h * new_w) / orig_w)
                    img = self.load_image(p_path, new_w, new_h)
                    self.player_images.append(img)
            except Exception: 
                self.player_images.append(None)
                
        self.gif_frames = []
        gif_path = resource_path("img/fireworks/giphy.gif")
        if os.path.exists(gif_path) and HAS_PILLOW:
            with Image.open(gif_path) as im:
                for frame in range(im.n_frames):
                    im.seek(frame)
                    frame_image = im.resize((self.width, self.height), Image.Resampling.LANCZOS).convert("RGBA")
                    self.gif_frames.append(ImageTk.PhotoImage(frame_image))
    

    def play_sound(self, sound_file):
        if PYGAME_AVAILABLE:
            try:
                s = pygame.mixer.Sound(resource_path(f"sounds/{sound_file}"))
                s.play()
            except: pass


    def clear_canvas(self):
        if hasattr(self, 'gif_after_id'):
            self.root.after_cancel(self.gif_after_id)
        self.canvas.delete("all")
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop() 
            pygame.mixer.stop()       


    def show_scene_start(self):
        self.positions = {}
        self.players_count = 2
        self.current_player = 1
        self.clear_canvas()
        if self.images.get('bg_start'): self.canvas.create_image(0, 0, image=self.images['bg_start'], anchor="nw")
        
        cx, cy = self.width // 2, self.height // 2
        self.canvas.create_image(cx, cy - 120, image=self.btn_anims['start']['normal'], tags="btn_start")
        self.canvas.create_image(cx, cy + 60, image=self.btn_anims['rules']['normal'], tags="btn_rules")
        
        self.bind_animated_button("btn_start", self.btn_anims['start'], lambda: self.show_scene_players())
        self.bind_animated_button("btn_rules", self.btn_anims['rules'], lambda: self.show_scene_rules())


    def show_scene_rules(self):
        self.clear_canvas()
        cx, cy = self.width // 2, self.height // 2
        if self.images.get('bg_rules'): self.canvas.create_image(0, 0, image=self.images['bg_rules'], anchor="nw")
        
        if PYGAME_AVAILABLE:
            try: pygame.mixer.Sound(resource_path("sounds/Правила.wav")).play()
            except: pass
            
        self.canvas.create_image(cx + 700, cy + 360, image=self.btn_anims['house_small']['normal'], tags="home")
        self.bind_animated_button("home", self.btn_anims['house_small'], lambda: self.show_scene_start())


    def show_scene_players(self):
        self.clear_canvas()
        if self.images.get('bg_players'): self.canvas.create_image(0, 0, image=self.images['bg_players'], anchor="nw")
        
        cx, cy = self.width // 2, self.height // 2
        self.canvas.create_image(cx - 460, cy - 300, image=self.btn_anims['2p']['normal'], tags="btn_2p")
        self.bind_animated_button("btn_2p", self.btn_anims['2p'], lambda: self.set_players(2))
        
        self.canvas.create_image(cx, cy - 300, image=self.btn_anims['3p']['normal'], tags="btn_3p")
        self.bind_animated_button("btn_3p", self.btn_anims['3p'], lambda: self.set_players(3))
        
        self.canvas.create_image(cx + 460, cy - 300, image=self.btn_anims['4p']['normal'], tags="btn_4p")
        self.bind_animated_button("btn_4p", self.btn_anims['4p'], lambda: self.set_players(4))
        
        self.canvas.create_image(cx - 380, cy + 300, image=self.btn_anims['5p']['normal'], tags="btn_5p")
        self.bind_animated_button("btn_5p", self.btn_anims['5p'], lambda: self.set_players(5))
        
        self.canvas.create_image(cx + 380, cy + 300, image=self.btn_anims['6p']['normal'], tags="btn_6p")
        self.bind_animated_button("btn_6p", self.btn_anims['6p'], lambda: self.set_players(6))


    def set_players(self, count):
        self.players_count = count
        self.show_scene_difficulty()


    def show_scene_difficulty(self):
        self.clear_canvas()
        if self.images.get('bg_diff'): self.canvas.create_image(0, 0, image=self.images['bg_diff'], anchor="nw")
        
        cx, cy = self.width // 2, self.height // 2
        self.canvas.create_image(cx - 200, cy + 20, image=self.btn_anims['lesno']['normal'], tags="btn_lesno")
        self.canvas.create_image(cx + 200, cy + 20, image=self.btn_anims['trydno']['normal'], tags="btn_trydno")
        self.canvas.create_image(cx, cy + 190, image=self.btn_anims['vsiqko']['normal'], tags="btn_vsiqko")
        
        self.bind_animated_button("btn_lesno", self.btn_anims['lesno'], lambda: self.start_game("lesno"))
        self.bind_animated_button("btn_trydno", self.btn_anims['trydno'], lambda: self.start_game("trydno"))
        self.bind_animated_button("btn_vsiqko", self.btn_anims['vsiqko'], lambda: self.start_game("vsiqko"))


    def start_game(self, diff):
        global ALL_QUESTIONS
        ALL_QUESTIONS = load_questions_from_file("Въпроси.md")
        
        if diff == "lesno":
            self.active_questions = [q for q in ALL_QUESTIONS if q.get("diff", "").lower() == "лесно"]
        elif diff == "trydno":
            self.active_questions = [q for q in ALL_QUESTIONS if q.get("diff", "").lower() == "трудно"]
        else:
            self.active_questions = ALL_QUESTIONS.copy()
            
        if not self.active_questions:
            self.active_questions = [{"q": "Няма намерени въпроси за това ниво!", "a": "error", "diff": "Лесно"}]
            
        self.current_player = 1
        for i in range(1, self.players_count + 1): self.positions[i] = 0
        self.show_scene_game()


    def show_scene_game(self):
        self.current_scene = "game"
        self.canvas.delete("all")
        
        cx, cy = self.width // 2, self.height // 2
        self.board_x = cx - self.height // 2
        left_margin_center = self.board_x / 2
        right_margin_center = self.width - (self.board_x / 2)
        
        if self.images.get('bg_table'): self.canvas.create_image(0, 0, image=self.images['bg_table'], anchor="nw")
        self.canvas.create_image(cx, cy, image=self.images['bg_field'])
        
        self.zar_item = self.canvas.create_image(left_margin_center, int(200 * self.scale), image=self.zar_images['натисни'], tags="dice")
        
        self.canvas.tag_bind("dice", "<Button-1>", lambda e: self.roll_dice())
        self.canvas.tag_bind("dice", "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind("dice", "<Leave>", lambda e: self.canvas.config(cursor=""))
        
        max_text_width = int(self.board_x - 20)
        self.status_txt = self.canvas.create_text(left_margin_center, int(400 * self.scale), text="", font=("Arial", int(36 * self.scale), "bold"), fill="black", justify="center", width=max_text_width)
        
        self.canvas.create_image(right_margin_center, self.height - int(200 * self.scale), image=self.btn_anims['house']['normal'], tags="home_btn")
        self.bind_animated_button("home_btn", self.btn_anims['house'], self.confirm_exit_to_start)
        
        self.update_status_msg()
        self.draw_players()
        

    def update_status_msg(self):
        msg = f"Ред: \nИграч {self.current_player}"
        self.canvas.itemconfig(self.status_txt, text=msg)


    def draw_players(self):
        self.canvas.delete("player_token")
        font_size = max(12, int(14 * self.scale))
        board_size = self.height
        cell_size  = board_size / 10
        board_top  = (self.height - board_size) / 2
        
        def cell_center(pos):
            z      = pos - 1
            row_b  = z // 10
            col_b  = z % 10 if row_b % 2 == 0 else 9 - (z % 10)
            cx_cell = self.board_x + col_b * cell_size + cell_size / 2
            cy_cell = board_top + board_size - row_b * cell_size - cell_size / 2
            return cx_cell, cy_cell
            
        step = cell_size / 3
        multi_offsets = [(-step/2, -step), ( step/2, -step), (-step/2, 0), ( step/2, 0), (-step/2, step), ( step/2, step)]
        
        from collections import defaultdict
        pos_groups = defaultdict(list)
        for p_id, pos in self.positions.items(): pos_groups[pos].append(p_id)
        
        left_margin_center = self.board_x / 2
        col_gap, row_spacing = 100, int(self.height * 0.14)
        base_y, col_positions = self.height - int(80 * self.scale), [left_margin_center - 50, left_margin_center + 50]
        
        for p_id in pos_groups[0]:
            col, row = (p_id - 1) % 2, (p_id - 1) // 2
            px, label_y = col_positions[col], base_y - row * row_spacing
            avatar_y = label_y - 15 - int(cell_size * 0.4)
            self.canvas.create_text(px, label_y, text=f"Играч {p_id}", fill="black", font=("Arial", font_size, "bold"), tags="player_token")
            if p_id - 1 < len(self.player_images):
                img = self.player_images[p_id - 1]
                if img: self.canvas.create_image(px, avatar_y, image=img, tags="player_token")
                
        for pos, players_here in pos_groups.items():
            if pos == 0: continue
            cx_cell, cy_cell = cell_center(pos)
            count = len(players_here)
            for local_idx, p_id in enumerate(players_here):
                px, py = (cx_cell, cy_cell) if count == 1 else (cx_cell + multi_offsets[local_idx % 6][0], cy_cell + multi_offsets[local_idx % 6][1])
                if p_id - 1 < len(self.player_images):
                    img = self.player_images[p_id - 1]
                    if img: self.canvas.create_image(px, py, image=img, tags="player_token")


    def _animate_then_roll(self, final_val, step):
        if step < 8:
            self.canvas.itemconfig(self.zar_item, image=self.zar_images[random.randint(1, 6)])
            self.root.after(70, lambda: self._animate_then_roll(final_val, step + 1))
        else: self._do_roll(final_val)


    def _do_roll(self, zar_value):
        self.canvas.itemconfig(self.zar_item, image=self.zar_images[zar_value])
        start_pos = self.positions[self.current_player]
        target_pos = start_pos + zar_value
        
        if target_pos > 100: self.next_turn()
        else: self.move_player_stepwise(start_pos, target_pos)


    def roll_dice(self):
        if self.is_moving: return
        
        self.is_moving = True
        if PYGAME_AVAILABLE:
            try: pygame.mixer.Sound(resource_path("sounds/dice_sound.wav")).play()
            except: pass
        self._animate_then_roll(random.randint(1, 6), 0)


    def move_player_stepwise(self, current, target):
        if current < target:
            self.positions[self.current_player] = current + 1
            self.draw_players()
            self.root.update()
            self.root.after(150, lambda: self.move_player_stepwise(current + 1, target))
        else:
            if target == 100: self.show_scene_win()
            elif target in SPECIAL_SQUARES: self.handle_special(target)
            else: self.next_turn()
                

    def is_answer_correct(self, q_text, correct_ans, user_ans):
        user_ans, correct_ans = user_ans.strip().lower(), correct_ans.strip().lower()
        if user_ans == "%" or user_ans == correct_ans: return True
        if user_ans + " г." == correct_ans or user_ans + " в." == correct_ans: return True
        
        if "(" in q_text and ")" in q_text and "???" in q_text:
            template = q_text[q_text.find("(")+1:q_text.find(")")] 
            if template.replace("???", user_ans).strip().lower() == correct_ans: return True
            
        return False


    def ask_question_with_timer(self, q):
        timer_secs = q.get("timer", 60)
        result = {"ans": None, "timed_out": False}

        win = tk.Toplevel(self.root)
        win.title("Въпрос")
        win.grab_set()
        win.resizable(False, False)

        win_w, win_h = 700, 380
        sx = self.root.winfo_screenwidth()
        sy = self.root.winfo_screenheight()
        win.geometry(f"{win_w}x{win_h}+{(sx-win_w)//2}+{(sy-win_h)//2}")

        tk.Label(win, text=f"Ниво: {q['diff']}", font=("Arial", 11, "italic"), fg="#555").pack(pady=(12, 0))

        tk.Label(win, text=q['q'], font=("Arial", 14, "bold"),
                 wraplength=660, justify="center").pack(padx=20, pady=10)

        entry_frame = tk.Frame(win)
        entry_frame.pack(pady=5)
        tk.Label(entry_frame, text="Отговор:", font=("Arial", 12)).pack(side="left", padx=5)
        entry = tk.Entry(entry_frame, font=("Arial", 13), width=30)
        entry.pack(side="left")
        entry.focus_set()

        BAR_W, BAR_H = 660, 34
        timer_canvas = tk.Canvas(win, width=BAR_W, height=BAR_H, highlightthickness=0, bg=win.cget("bg"))
        timer_canvas.pack(pady=15)
        
        timer_canvas.create_rectangle(0, 0, BAR_W, BAR_H, fill="#d3d3d3", outline="#a9a9a9") 
        
        bar_rect = timer_canvas.create_rectangle(0, 0, BAR_W, BAR_H, fill="#4CAF50", outline="")
        
        bar_text = timer_canvas.create_text(BAR_W // 2, BAR_H // 2,
                                            text=str(timer_secs),
                                            font=("Arial", 16, "bold"), fill="black")

        def submit(event=None):
            result["ans"] = entry.get()
            win.destroy()

        tk.Button(win, text="ОТГОВОРИ", command=submit,
                  bg="#2196F3", fg="white", 
                  font=("Arial", 16, "bold"),
                  width=20,
                  height=1,
                  cursor="hand2",
                  relief="raised").pack(pady=15)
        
        entry.bind("<Return>", submit)
        
        remaining = [timer_secs]

        def tick():
            if not win.winfo_exists():
                return
            remaining[0] -= 1
            frac = remaining[0] / timer_secs
            new_w = int(BAR_W * frac)
            
            if frac > 0.5:
                r, g = int(255 * (1 - frac) * 2), 200
            else:
                r, g = 255, int(200 * frac * 2)
            color = f"#{r:02x}{g:02x}00"
            
            timer_canvas.coords(bar_rect, 0, 0, new_w, BAR_H)
            timer_canvas.itemconfig(bar_rect, fill=color)
            timer_canvas.itemconfig(bar_text, text=str(remaining[0]))

            if remaining[0] <= 0:
                result["timed_out"] = True
                win.destroy()
            else:
                win.after(1000, tick)

        win.after(1000, tick)
        win.wait_window()

        if result["timed_out"]:
            return None
        return result["ans"]


    def handle_special(self, pos):
        q = random.choice(self.active_questions)
        ans = self.ask_question_with_timer(q)
        
        if ans and self.is_answer_correct(q['q'], q['a'], ans):
            if PYGAME_AVAILABLE:
                try: pygame.mixer.Sound(resource_path("sounds/wow.mp3")).play()
                except: pass
            if HAS_PILLOW: self.flash('bg_correct')
            if pos in LADDERS: self.positions[self.current_player] = LADDERS[pos]
        else:
            if PYGAME_AVAILABLE:
                try: pygame.mixer.Sound(resource_path("sounds/sad.wav")).play()
                except: pass
            if HAS_PILLOW: self.flash('bg_wrong')
            messagebox.showinfo("Грешен отговор", f"Правилният отговор е: {q['a']}")
            if pos in SNAKES: self.positions[self.current_player] = SNAKES[pos]
            
        self.draw_players(); self.next_turn()


    def flash(self, key):
        f = self.canvas.create_image(0, 0, image=self.images[key], anchor="nw")
        self.root.update(); time.sleep(1); self.canvas.delete(f)


    def next_turn(self):
        self.is_moving = False
        self.current_player = (self.current_player % self.players_count) + 1
        self.update_status_msg()
        self.canvas.itemconfig(self.zar_item, image=self.zar_images['натисни'])


    def show_scene_win(self):
        self.clear_canvas()
        if self.images.get('bg_win'): self.canvas.create_image(0, 0, image=self.images['bg_win'], anchor="nw")
        
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.music.load(resource_path("sounds/fireworks.mp3"))
                pygame.mixer.music.play()
            except Exception as e: pass

        if hasattr(self, 'gif_frames') and self.gif_frames:
            self.gif_item = self.canvas.create_image(self.width//2, self.height//2, image=self.gif_frames[0])
            self.animate_gif(0)
            
        p_path = resource_path(f"img/players/p{self.current_player}.png")
        if HAS_PILLOW and os.path.exists(p_path):
            with Image.open(p_path) as win_img:
                large_w = int(450 * self.scale)
                orig_w, orig_h = win_img.size
                large_h = int((orig_h * large_w) / orig_w)
                self.win_avatar_photo = ImageTk.PhotoImage(win_img.resize((large_w, large_h), Image.Resampling.LANCZOS))
                self.canvas.create_image(self.width//2, self.height//2 - 50, image=self.win_avatar_photo)

        msg = f"ИГРАЧ {self.current_player} ПОБЕДИ!"
        fnt = ("Arial", int(80 * self.scale), "bold")
        for dx, dy in [(-3,-3), (3,-3), (-3,3), (3,3), (0,-3), (-3,0), (3,0), (0,3)]:
            self.canvas.create_text(self.width//2 + dx, self.height//2 + 280 + dy, text=msg, font=fnt, fill="black")
        self.canvas.create_text(self.width//2, self.height//2 + 280, text=msg, font=fnt, fill="white")
        
        hx = int(150 * self.scale)
        hy = self.height - int(150 * self.scale)
        self.canvas.create_image(hx, hy, image=self.btn_anims['house']['normal'], tags="home_btn_win")
        self.bind_animated_button("home_btn_win", self.btn_anims['house'], lambda: self.show_scene_start())
        

    def animate_gif(self, frame_idx):
        if not hasattr(self, 'gif_frames') or not self.gif_frames: return
        frame_idx = (frame_idx + 1) % len(self.gif_frames)
        self.canvas.itemconfig(self.gif_item, image=self.gif_frames[frame_idx])
        self.gif_after_id = self.root.after(50, self.animate_gif, frame_idx)


    def confirm_exit_to_start(self):
        if messagebox.askyesno("Изход", "Сигурен ли си?"): self.show_scene_start()


    def exit_game(self):
        if PYGAME_AVAILABLE:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FullscreenGameApp(root)
    root.mainloop()