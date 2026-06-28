"""
Sudoku — Kivy Mobile App  v3
New in this version:
  Gameplay:
    • Undo (move stack, including pencil marks)
    • Auto-remove pencil marks when a number is placed in same row/col/box
    • Numpad buttons dim when that digit is fully placed (9 times)
  Polish:
    • Correct entry: brief green flash on the cell (Kivy Animation)
    • Wrong entry: red shake animation on the cell
    • Win animation: cells light up in wave sequence before popup
    • Restart confirmation popup
  Progression:
    • Best times stored per difficulty via Kivy JsonStore
    • Daily streak counter (puzzles completed today)
    • Stats shown on main menu
  Settings screen:
    • Sound on/off
    • Haptic on/off
    • Auto-check mistakes on/off (if off, conflicts only shown on request)
"""

import random, time, struct, wave, io, tempfile, math, json
from datetime import date

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition, SlideTransition
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.switch import Switch
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.animation import Animation
from kivy.metrics import dp, sp
from kivy.storage.jsonstore import JsonStore

try:
    from plyer import vibrator
    HAS_VIBRATOR = True
except Exception:
    HAS_VIBRATOR = False

# ============================================================
# PERSISTENT STORE
# ============================================================

store = JsonStore('sudoku_data.json')

def _load_settings():
    if store.exists('settings'):
        return store.get('settings')
    return {'sound': True, 'haptic': True, 'auto_check': True}

def _save_settings(s):
    store.put('settings', **s)

def _load_stats():
    if store.exists('stats'):
        return store.get('stats')
    return {
        'best_easy': 0, 'best_medium': 0, 'best_hard': 0, 'best_expert': 0,
        'streak': 0, 'last_date': '', 'total': 0,
    }

def _save_stats(s):
    store.put('stats', **s)

SETTINGS = _load_settings()
STATS    = _load_stats()

# ============================================================
# THEMES
# ============================================================

THEMES = {
    "Tokyo Night": {
        "bg":           (0.059, 0.063, 0.122, 1),
        "grid_border":  (0.404, 0.506, 0.780, 1),
        "cell_bg":      (0.102, 0.114, 0.188, 1),
        "selected":     (0.271, 0.404, 0.780, 1),
        "highlight":    (0.141, 0.161, 0.271, 1),
        "same_num":     (0.180, 0.259, 0.502, 1),
        "given_fg":     (0.788, 0.831, 0.984, 1),
        "user_fg":      (0.380, 0.851, 0.620, 1),
        "conflict_fg":  (1.000, 0.471, 0.471, 1),
        "pencil_fg":    (0.961, 0.800, 0.400, 1),
        "accent":       (0.569, 0.408, 0.882, 1),
        "btn_bg":       (0.141, 0.161, 0.271, 1),
        "btn_fg":       (0.788, 0.831, 0.984, 1),
        "del_bg":       (0.502, 0.118, 0.118, 1),
        "del_fg":       (1.000, 0.471, 0.471, 1),
        "pencil_btn_fg":(0.961, 0.800, 0.400, 1),
        "hint_fg":      (0.569, 0.408, 0.882, 1),
        "title_fg":     (0.569, 0.408, 0.882, 1),
        "flash_ok":     (0.380, 0.851, 0.620, 1),
        "flash_err":    (1.000, 0.271, 0.271, 1),
    },
    "Gruvbox Dark": {
        "bg":           (0.157, 0.141, 0.129, 1),
        "grid_border":  (0.839, 0.600, 0.251, 1),
        "cell_bg":      (0.235, 0.212, 0.196, 1),
        "selected":     (0.839, 0.600, 0.251, 1),
        "highlight":    (0.314, 0.286, 0.263, 1),
        "same_num":     (0.549, 0.404, 0.169, 1),
        "given_fg":     (0.922, 0.859, 0.698, 1),
        "user_fg":      (0.722, 0.733, 0.149, 1),
        "conflict_fg":  (0.984, 0.286, 0.200, 1),
        "pencil_fg":    (0.992, 0.776, 0.118, 1),
        "accent":       (0.839, 0.600, 0.251, 1),
        "btn_bg":       (0.314, 0.286, 0.263, 1),
        "btn_fg":       (0.922, 0.859, 0.698, 1),
        "del_bg":       (0.573, 0.153, 0.118, 1),
        "del_fg":       (0.984, 0.286, 0.200, 1),
        "pencil_btn_fg":(0.992, 0.776, 0.118, 1),
        "hint_fg":      (0.839, 0.600, 0.251, 1),
        "title_fg":     (0.992, 0.776, 0.118, 1),
        "flash_ok":     (0.722, 0.733, 0.149, 1),
        "flash_err":    (0.984, 0.286, 0.200, 1),
    },
    "Catppuccin": {
        "bg":           (0.094, 0.094, 0.137, 1),
        "grid_border":  (0.529, 0.467, 0.824, 1),
        "cell_bg":      (0.122, 0.122, 0.180, 1),
        "selected":     (0.529, 0.467, 0.824, 1),
        "highlight":    (0.180, 0.180, 0.271, 1),
        "same_num":     (0.337, 0.302, 0.557, 1),
        "given_fg":     (0.808, 0.839, 0.957, 1),
        "user_fg":      (0.651, 0.890, 0.631, 1),
        "conflict_fg":  (0.953, 0.545, 0.659, 1),
        "pencil_fg":    (0.980, 0.839, 0.490, 1),
        "accent":       (0.529, 0.467, 0.824, 1),
        "btn_bg":       (0.180, 0.180, 0.271, 1),
        "btn_fg":       (0.808, 0.839, 0.957, 1),
        "del_bg":       (0.502, 0.169, 0.259, 1),
        "del_fg":       (0.953, 0.545, 0.659, 1),
        "pencil_btn_fg":(0.980, 0.839, 0.490, 1),
        "hint_fg":      (0.529, 0.467, 0.824, 1),
        "title_fg":     (0.529, 0.467, 0.824, 1),
        "flash_ok":     (0.651, 0.890, 0.631, 1),
        "flash_err":    (0.953, 0.545, 0.659, 1),
    },
    "Nord": {
        "bg":           (0.180, 0.204, 0.251, 1),
        "grid_border":  (0.533, 0.753, 0.816, 1),
        "cell_bg":      (0.231, 0.259, 0.322, 1),
        "selected":     (0.533, 0.753, 0.816, 1),
        "highlight":    (0.298, 0.337, 0.416, 1),
        "same_num":     (0.322, 0.506, 0.573, 1),
        "given_fg":     (0.898, 0.914, 0.941, 1),
        "user_fg":      (0.639, 0.745, 0.549, 1),
        "conflict_fg":  (0.749, 0.380, 0.416, 1),
        "pencil_fg":    (0.922, 0.796, 0.545, 1),
        "accent":       (0.533, 0.753, 0.816, 1),
        "btn_bg":       (0.298, 0.337, 0.416, 1),
        "btn_fg":       (0.898, 0.914, 0.941, 1),
        "del_bg":       (0.431, 0.200, 0.216, 1),
        "del_fg":       (0.749, 0.380, 0.416, 1),
        "pencil_btn_fg":(0.922, 0.796, 0.545, 1),
        "hint_fg":      (0.533, 0.753, 0.816, 1),
        "title_fg":     (0.533, 0.753, 0.816, 1),
        "flash_ok":     (0.639, 0.745, 0.549, 1),
        "flash_err":    (0.749, 0.380, 0.416, 1),
    },
    "Solarized Light": {
        "bg":           (0.992, 0.965, 0.890, 1),
        "grid_border":  (0.149, 0.545, 0.824, 1),
        "cell_bg":      (0.933, 0.910, 0.835, 1),
        "selected":     (0.149, 0.545, 0.824, 1),
        "highlight":    (0.863, 0.843, 0.769, 1),
        "same_num":     (0.400, 0.671, 0.863, 1),
        "given_fg":     (0.027, 0.212, 0.259, 1),
        "user_fg":      (0.522, 0.600, 0.000, 1),
        "conflict_fg":  (0.863, 0.196, 0.184, 1),
        "pencil_fg":    (0.796, 0.294, 0.086, 1),
        "accent":       (0.149, 0.545, 0.824, 1),
        "btn_bg":       (0.863, 0.843, 0.769, 1),
        "btn_fg":       (0.027, 0.212, 0.259, 1),
        "del_bg":       (0.863, 0.196, 0.184, 0.2),
        "del_fg":       (0.863, 0.196, 0.184, 1),
        "pencil_btn_fg":(0.796, 0.294, 0.086, 1),
        "hint_fg":      (0.149, 0.545, 0.824, 1),
        "title_fg":     (0.149, 0.545, 0.824, 1),
        "flash_ok":     (0.522, 0.600, 0.000, 1),
        "flash_err":    (0.863, 0.196, 0.184, 1),
    },
}

THEME_NAMES = list(THEMES.keys())
active_theme = THEMES["Tokyo Night"]

# ============================================================
# AUDIO
# ============================================================

def _make_wav(freq, duration, volume=0.5, sample_rate=22050):
    n = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n):
            env = max(0.0, 1.0 - i / n)
            s = int(volume * env * 32767 * math.sin(2 * math.pi * freq * i / sample_rate))
            frames += struct.pack('<h', s)
        wf.writeframes(bytes(frames))
    tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    tmp.write(buf.getvalue())
    tmp.close()
    return tmp.name

_sounds = {}

def _get_sound(key):
    if key not in _sounds:
        if key == 'error':
            _sounds[key] = SoundLoader.load(_make_wav(180, 0.12))
        elif key == 'correct':
            _sounds[key] = SoundLoader.load(_make_wav(880, 0.06, volume=0.3))
        elif key == 'win':
            _sounds[key] = SoundLoader.load(_make_wav(660, 0.25, volume=0.4))
    return _sounds.get(key)

def play_sound(key):
    if not SETTINGS.get('sound', True):
        return
    snd = _get_sound(key)
    if snd:
        snd.play()

def do_haptic(duration=0.05):
    if not SETTINGS.get('haptic', True):
        return
    if HAS_VIBRATOR:
        try:
            vibrator.vibrate(duration)
        except Exception:
            pass

# ============================================================
# SUDOKU LOGIC
# ============================================================

def generate_solution():
    base = 3
    side = base * base
    def pattern(r, c): return (base * (r % base) + r // base + c) % side
    rB = range(base)
    rows = [g * base + r for g in random.sample(rB, base) for r in random.sample(rB, base)]
    cols = [g * base + c for g in random.sample(rB, base) for c in random.sample(rB, base)]
    nums = random.sample(range(1, side + 1), side)
    return [[nums[pattern(r, c)] for c in cols] for r in rows]

def make_puzzle(solution, difficulty):
    puzzle = [row[:] for row in solution]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    removals = {'easy': 36, 'medium': 46, 'hard': 52, 'expert': 56}[difficulty]
    for r, c in cells[:removals]:
        puzzle[r][c] = 0
    return puzzle

def find_conflicts(board):
    cf = set()
    for r in range(9):
        for c in range(9):
            v = board[r][c]
            if not v:
                continue
            bad = False
            for i in range(9):
                if i != c and board[r][i] == v: bad = True
                if i != r and board[i][c] == v: bad = True
            if not bad:
                br, bc = (r // 3) * 3, (c // 3) * 3
                for i in range(3):
                    for j in range(3):
                        if (br+i, bc+j) != (r, c) and board[br+i][bc+j] == v:
                            bad = True
            if bad:
                cf.add((r, c))
    return cf

def count_placed(board):
    """Return dict of how many times each digit 1-9 is placed."""
    counts = {n: 0 for n in range(1, 10)}
    for row in board:
        for v in row:
            if v:
                counts[v] += 1
    return counts

# ============================================================
# GAME STATE
# ============================================================

class Game:
    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty
        self.solution   = generate_solution()
        self.puzzle     = make_puzzle(self.solution, difficulty)
        self.board      = [row[:] for row in self.puzzle]
        self.givens     = {(r, c) for r in range(9) for c in range(9) if self.puzzle[r][c] != 0}
        self.pencils    = {}
        self.selected   = (4, 4)
        self.pencil_mode = False
        self.start_time = time.time()
        self.mistakes   = 0
        self.max_mistakes = 5
        self.won  = False
        self.lost = False
        self._dirty = True
        self._conflict_cache = set()
        # Undo stack: each entry is (board_snapshot, pencils_snapshot, mistakes)
        self._undo_stack = []

    def _snapshot(self):
        return (
            [row[:] for row in self.board],
            {k: set(v) for k, v in self.pencils.items()},
            self.mistakes,
        )

    def _push_undo(self):
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > 100:
            self._undo_stack.pop(0)

    def undo(self):
        if not self._undo_stack:
            return False
        board, pencils, mistakes = self._undo_stack.pop()
        self.board    = board
        self.pencils  = pencils
        self.mistakes = mistakes
        self._dirty   = True
        self.won  = False
        self.lost = False
        return True

    def conflicts(self):
        if self._dirty:
            auto = SETTINGS.get('auto_check', True)
            self._conflict_cache = find_conflicts(self.board) if auto else set()
            self._dirty = False
        return self._conflict_cache

    def _clear_pencil_marks(self, r, c, v):
        """Remove digit v from pencil marks in same row, col, and box."""
        br, bc = (r // 3) * 3, (c // 3) * 3
        affected = (
            [(r, cc) for cc in range(9)] +
            [(rr, c) for rr in range(9)] +
            [(br + i, bc + j) for i in range(3) for j in range(3)]
        )
        for pos in affected:
            if pos in self.pencils:
                self.pencils[pos].discard(v)
                if not self.pencils[pos]:
                    del self.pencils[pos]

    def input(self, num):
        """Returns 'error', 'correct', or None."""
        if self.won or self.lost:
            return None
        r, c = self.selected
        if (r, c) in self.givens:
            return None

        self._push_undo()

        if self.pencil_mode:
            if num == 0:
                self.pencils.pop((r, c), None)
            elif self.board[r][c] == 0:
                marks = self.pencils.setdefault((r, c), set())
                if num in marks: marks.discard(num)
                else: marks.add(num)
            return None
        else:
            if num == 0:
                if self.board[r][c] == 0 and (r, c) not in self.pencils:
                    self._undo_stack.pop()  # nothing changed
                    return None
                self.board[r][c] = 0
                self.pencils.pop((r, c), None)
                self._dirty = True
                return None
            else:
                self.board[r][c] = num
                self.pencils.pop((r, c), None)
                self._dirty = True
                if self.solution[r][c] != num:
                    self.mistakes += 1
                    if self.mistakes >= self.max_mistakes:
                        self.lost = True
                    return 'error'
                else:
                    self._clear_pencil_marks(r, c, num)
                    if all(
                        self.board[i][j] == self.solution[i][j]
                        for i in range(9) for j in range(9)
                    ):
                        self.won = True
                    return 'correct'

    def hint(self):
        if self.won or self.lost:
            return
        r, c = self.selected
        if (r, c) in self.givens or self.board[r][c] == self.solution[r][c]:
            empties = [(i, j) for i in range(9) for j in range(9) if self.board[i][j] == 0]
            if not empties:
                return
            r, c = random.choice(empties)
            self.selected = (r, c)
        self._push_undo()
        v = self.solution[r][c]
        self.board[r][c] = v
        self.pencils.pop((r, c), None)
        self._clear_pencil_marks(r, c, v)
        self._dirty = True
        if all(self.board[i][j] == self.solution[i][j] for i in range(9) for j in range(9)):
            self.won = True

    def restart(self):
        self.board    = [row[:] for row in self.puzzle]
        self.pencils  = {}
        self.mistakes = 0
        self.start_time = time.time()
        self.won  = False
        self.lost = False
        self._dirty = True
        self._undo_stack.clear()

    def elapsed(self):
        return int(time.time() - self.start_time)

# ============================================================
# HELPERS
# ============================================================

def apply_bg(widget, color):
    with widget.canvas.before:
        c = Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, v: setattr(rect, 'pos', w.pos))
    widget.bind(size=lambda w, v: setattr(rect, 'size', w.size))
    return rect

def mk_btn(text, fg, bg, font_size='15sp', bold=True):
    return Button(
        text=text, color=fg,
        background_normal='', background_down='',
        background_color=bg, bold=bold, font_size=font_size,
    )

def _base_popup(title, content, size_hint=(0.85, 0.55)):
    t = active_theme
    p = Popup(
        title=title, title_color=t['title_fg'],
        content=content, size_hint=size_hint,
        separator_color=t['accent'],
        background_color=t['bg'], background='',
    )
    return p

# ============================================================
# POPUPS
# ============================================================

def difficulty_popup(on_choose):
    t = active_theme
    layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))
    apply_bg(layout, t['bg'])
    p = [None]
    layout.add_widget(Label(text="Choose Difficulty", color=t['title_fg'],
                            bold=True, font_size='17sp', size_hint_y=0.2))
    colors = {'Easy': t['user_fg'], 'Medium': t['given_fg'],
              'Hard': t['pencil_fg'], 'Expert': t['conflict_fg']}
    for diff, fg in colors.items():
        btn = mk_btn(diff, fg, t['btn_bg'], font_size='16sp')
        def _cb(inst, d=diff.lower()):
            p[0].dismiss()
            on_choose(d)
        btn.bind(on_press=_cb)
        layout.add_widget(btn)
    cancel = mk_btn("Cancel", t['btn_fg'], t['del_bg'], font_size='14sp')
    cancel.size_hint_y = 0.7
    cancel.bind(on_press=lambda *_: p[0].dismiss())
    layout.add_widget(cancel)
    p[0] = _base_popup("New Game", layout, size_hint=(0.80, 0.65))
    p[0].open()

def confirm_popup(title, message, on_confirm):
    t = active_theme
    layout = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(14))
    apply_bg(layout, t['bg'])
    p = [None]
    layout.add_widget(Label(text=message, color=t['given_fg'], font_size='15sp',
                            size_hint_y=0.5, halign='center', valign='middle'))
    row = BoxLayout(spacing=dp(8), size_hint_y=0.4)
    yes = mk_btn("Yes", t['conflict_fg'], t['del_bg'], font_size='15sp')
    no  = mk_btn("No",  t['user_fg'],    t['btn_bg'], font_size='15sp')
    yes.bind(on_press=lambda *_: [p[0].dismiss(), on_confirm()])
    no.bind(on_press=lambda *_: p[0].dismiss())
    row.add_widget(yes)
    row.add_widget(no)
    layout.add_widget(row)
    p[0] = _base_popup(title, layout, size_hint=(0.78, 0.38))
    p[0].open()

def result_popup(won, elapsed, mistakes, difficulty, on_new, on_restart, on_menu):
    t = active_theme
    layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(14))
    apply_bg(layout, t['bg'])
    p = [None]

    if won:
        title = "Puzzle Solved!"
        m, s = divmod(elapsed, 60)
        time_str = f"{m:02d}:{s:02d}"
        best_key = f'best_{difficulty}'
        prev_best = STATS.get(best_key, 0)
        is_best = (prev_best == 0 or elapsed < prev_best)
        if is_best:
            STATS[best_key] = elapsed
        today = str(date.today())
        if STATS.get('last_date') == today:
            STATS['streak'] = STATS.get('streak', 0) + 1
        else:
            STATS['streak'] = 1
            STATS['last_date'] = today
        STATS['total'] = STATS.get('total', 0) + 1
        _save_stats(STATS)

        layout.add_widget(Label(text=title, color=t['title_fg'], bold=True,
                                font_size='20sp', size_hint_y=0.2))
        layout.add_widget(Label(text=f"Time: {time_str}   Mistakes: {mistakes}/5",
                                color=t['user_fg'], font_size='15sp', size_hint_y=0.15))
        pb_text = f"New best: {time_str}!" if is_best else f"Best: {_fmt_time(prev_best)}"
        layout.add_widget(Label(text=pb_text, color=t['pencil_fg'],
                                font_size='14sp', size_hint_y=0.12))
        layout.add_widget(Label(text=f"Streak: {STATS['streak']} today",
                                color=t['accent'], font_size='13sp', size_hint_y=0.1))
    else:
        title = "Game Over"
        layout.add_widget(Label(text=title, color=t['conflict_fg'], bold=True,
                                font_size='20sp', size_hint_y=0.3))
        layout.add_widget(Label(text="Too many mistakes!", color=t['given_fg'],
                                font_size='15sp', size_hint_y=0.2))

    def _go(fn):
        p[0].dismiss()
        fn()

    row = BoxLayout(spacing=dp(8), size_hint_y=0.28)
    for label, fn, fg in [
        ("New Game", on_new,     t['user_fg']),
        ("Restart",  on_restart, t['pencil_fg']),
        ("Menu",     on_menu,    t['given_fg']),
    ]:
        btn = mk_btn(label, fg, t['btn_bg'], font_size='13sp')
        btn.bind(on_press=lambda inst, f=fn: _go(f))
        row.add_widget(btn)
    layout.add_widget(row)

    p[0] = _base_popup(title, layout, size_hint=(0.88, 0.58 if won else 0.44))
    p[0].open()

def theme_popup(on_choose):
    t = active_theme
    layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))
    apply_bg(layout, t['bg'])
    p = [None]
    layout.add_widget(Label(text="Choose Theme", color=t['title_fg'], bold=True,
                            font_size='17sp', size_hint_y=0.15))
    for name in THEME_NAMES:
        th = THEMES[name]
        btn = mk_btn(name, th['given_fg'], th['cell_bg'], font_size='15sp')
        def _cb(inst, n=name):
            p[0].dismiss()
            on_choose(n)
        btn.bind(on_press=_cb)
        layout.add_widget(btn)
    cancel = mk_btn("Cancel", t['btn_fg'], t['del_bg'], font_size='14sp')
    cancel.size_hint_y = 0.7
    cancel.bind(on_press=lambda *_: p[0].dismiss())
    layout.add_widget(cancel)
    p[0] = _base_popup("Themes", layout, size_hint=(0.82, 0.75))
    p[0].open()

def _fmt_time(secs):
    if not secs:
        return "--:--"
    m, s = divmod(secs, 60)
    return f"{m:02d}:{s:02d}"

# ============================================================
# MAIN MENU SCREEN
# ============================================================

class MainMenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def on_enter(self):
        self._build()  # refresh stats each time we return

    def _build(self):
        self.clear_widgets()
        t = active_theme
        root = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(10))
        apply_bg(root, t['bg'])

        root.add_widget(Label(text="SUDOKU", color=t['title_fg'], bold=True,
                              font_size='46sp', size_hint_y=0.18))
        root.add_widget(Label(text="number puzzle", color=t['given_fg'],
                              font_size='13sp', size_hint_y=0.06))

        # Stats bar
        streak = STATS.get('streak', 0)
        total  = STATS.get('total', 0)
        stats_label = Label(
            text=f"{streak} today   ·   {total} solved",
            color=t['accent'], font_size='13sp', size_hint_y=0.07,
        )
        root.add_widget(stats_label)

        # Best times
        best_box = GridLayout(cols=4, spacing=dp(4), size_hint_y=0.1)
        for diff in ['easy', 'medium', 'hard', 'expert']:
            best = STATS.get(f'best_{diff}', 0)
            col = BoxLayout(orientation='vertical')
            col.add_widget(Label(text=diff[:3].upper(), color=t['accent'],
                                 bold=True, font_size='11sp'))
            col.add_widget(Label(text=_fmt_time(best), color=t['pencil_fg'],
                                 font_size='12sp'))
            best_box.add_widget(col)
        root.add_widget(best_box)

        root.add_widget(Label(text="Select Difficulty", color=t['accent'],
                              bold=True, font_size='14sp', size_hint_y=0.07))

        diff_colors = {
            'Easy':   t['user_fg'],
            'Medium': t['given_fg'],
            'Hard':   t['pencil_fg'],
            'Expert': t['conflict_fg'],
        }
        for diff, fg in diff_colors.items():
            btn = mk_btn(diff, fg, t['btn_bg'], font_size='17sp')
            btn.size_hint_y = 0.11
            btn.bind(on_press=lambda inst, d=diff.lower(): self._start(d))
            root.add_widget(btn)

        # Bottom row: Theme + Settings
        btm = BoxLayout(spacing=dp(8), size_hint_y=0.1)
        theme_btn = mk_btn("THEMES",   t['accent'],   t['btn_bg'], font_size='14sp')
        sett_btn  = mk_btn("SETTINGS", t['given_fg'], t['btn_bg'], font_size='14sp')
        theme_btn.bind(on_press=lambda *_: theme_popup(self._change_theme))
        sett_btn.bind(on_press=lambda *_: self.manager.current_screen.manager.current == 'menu'
                      and self._go_settings())
        sett_btn.bind(on_press=lambda *_: self._go_settings())
        btm.add_widget(theme_btn)
        btm.add_widget(sett_btn)
        root.add_widget(btm)

        self.add_widget(root)

    def _start(self, difficulty):
        gs = self.manager.get_screen('game')
        gs.start_new_game(difficulty)
        self.manager.current = 'game'

    def _change_theme(self, name):
        global active_theme
        active_theme = THEMES[name]
        self._build()

    def _go_settings(self):
        self.manager.get_screen('settings')._build()
        self.manager.current = 'settings'

# ============================================================
# SETTINGS SCREEN
# ============================================================

class SettingsScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        self.clear_widgets()
        t = active_theme
        root = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(12))
        apply_bg(root, t['bg'])

        root.add_widget(Label(text="Settings", color=t['title_fg'], bold=True,
                              font_size='26sp', size_hint_y=0.14))

        def row(label_text, key):
            box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(10))
            lbl = Label(text=label_text, color=t['given_fg'], font_size='15sp',
                        size_hint_x=0.7, halign='left', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            sw = Switch(active=SETTINGS.get(key, True), size_hint_x=0.3)
            def _on_change(inst, val, k=key):
                SETTINGS[k] = val
                _save_settings(SETTINGS)
            sw.bind(active=_on_change)
            box.add_widget(lbl)
            box.add_widget(sw)
            return box

        root.add_widget(row("Sound effects", 'sound'))
        root.add_widget(row("Haptic feedback", 'haptic'))
        root.add_widget(row("Auto-check mistakes\n(off = find errors yourself)", 'auto_check'))

        root.add_widget(Label(size_hint_y=None, height=dp(20)))  # spacer

        # Reset stats
        reset_btn = mk_btn("Reset Best Times & Stats", t['conflict_fg'], t['del_bg'], font_size='14sp')
        reset_btn.size_hint_y = None
        reset_btn.height = dp(48)
        def _reset(*_):
            confirm_popup("Reset Stats", "Clear all best times and streak?", self._do_reset)
        reset_btn.bind(on_press=_reset)
        root.add_widget(reset_btn)

        root.add_widget(Label(size_hint_y=1))  # push back button down

        back = mk_btn("← Back", t['accent'], t['btn_bg'], font_size='15sp')
        back.size_hint_y = None
        back.height = dp(48)
        back.bind(on_press=lambda *_: setattr(self.manager, 'current', 'menu'))
        root.add_widget(back)

        self.add_widget(root)

    def _do_reset(self):
        global STATS
        STATS = {
            'best_easy': 0, 'best_medium': 0, 'best_hard': 0, 'best_expert': 0,
            'streak': 0, 'last_date': '', 'total': 0,
        }
        _save_stats(STATS)

# ============================================================
# GAME SCREEN
# ============================================================

class GameScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.game = None
        self._result_shown = False
        self.cells = [[None]*9 for _ in range(9)]
        self._build_ui()

    def _build_ui(self):
        t = active_theme
        self._root = BoxLayout(orientation='vertical', padding=dp(6), spacing=dp(5))
        apply_bg(self._root, t['bg'])

        # Header
        self._header = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(4))
        self._lbl_diff     = Label(text="", color=t['accent'],       bold=True, font_size='14sp')
        self._lbl_time     = Label(text="00:00", color=t['given_fg'], bold=True, font_size='14sp')
        self._lbl_mistakes = Label(text="0/5", color=t['conflict_fg'],bold=True, font_size='14sp')
        self._header.add_widget(self._lbl_diff)
        self._header.add_widget(self._lbl_time)
        self._header.add_widget(self._lbl_mistakes)
        self._root.add_widget(self._header)

        # Grid
        self._outer = GridLayout(cols=3, spacing=dp(4))
        self._setup_bg(self._outer, t['grid_border'])
        for box_i in range(9):
            sub = GridLayout(cols=3, spacing=dp(1))
            self._setup_bg(sub, t['grid_border'])
            sr, sc = (box_i // 3) * 3, (box_i % 3) * 3
            for j in range(9):
                r, c = sr + j // 3, sc + j % 3
                cell = Button(
                    text='', color=t['given_fg'],
                    background_normal='', background_down='',
                    background_color=t['cell_bg'],
                    bold=True, font_size='26sp',
                )
                cell.row = r
                cell.col = c
                cell.bind(on_press=self._on_cell)
                self.cells[r][c] = cell
                sub.add_widget(cell)
            self._outer.add_widget(sub)
        self._root.add_widget(self._outer)

        # Numpad: 2 rows of 5 (1-9 + DEL)
        self._numpad = GridLayout(cols=5, spacing=dp(5), size_hint_y=None, height=dp(110))
        self._numpad_btns = []
        for i in range(1, 10):
            btn = mk_btn(str(i), t['accent'], t['btn_bg'], font_size='26sp')
            btn.bind(on_press=lambda inst, n=i: self._input(n))
            self._numpad.add_widget(btn)
            self._numpad_btns.append(btn)
        self._btn_del = mk_btn("DEL", t['del_fg'], t['del_bg'], font_size='26sp')
        self._btn_del.bind(on_press=lambda *_: self._input(0))
        self._numpad.add_widget(self._btn_del)
        self._root.add_widget(self._numpad)

        # Footer: Undo + Pencil + New + Hint + Theme
        self._footer = GridLayout(cols=5, spacing=dp(4), size_hint_y=None, height=dp(48))
        self._btn_undo   = mk_btn("UNDO",   t['given_fg'],       t['btn_bg'], font_size='13sp')
        self._btn_pencil = mk_btn("PENCIL", t["pencil_btn_fg"],  t['btn_bg'], font_size='13sp')
        self._btn_new    = mk_btn("New", t['given_fg'],   t['btn_bg'], font_size='13sp')
        self._btn_hint   = mk_btn("Hint",t['hint_fg'],    t['btn_bg'], font_size='13sp')
        self._btn_theme  = mk_btn("THEME", t["accent"],     t['btn_bg'], font_size='13sp')

        self._btn_undo.bind(on_press=self._undo)
        self._btn_pencil.bind(on_press=self._toggle_pencil)
        self._btn_new.bind(on_press=self._ask_new)
        self._btn_hint.bind(on_press=self._hint)
        self._btn_theme.bind(on_press=lambda *_: theme_popup(self._change_theme))

        for b in [self._btn_undo, self._btn_pencil, self._btn_new,
                  self._btn_hint, self._btn_theme]:
            self._footer.add_widget(b)
        self._root.add_widget(self._footer)
        self.add_widget(self._root)

    def _setup_bg(self, w, color):
        with w.canvas.before:
            c_inst = Color(*color)
            rect = Rectangle(pos=w.pos, size=w.size)
        w.bind(pos=lambda ww, v: setattr(rect, 'pos', ww.pos))
        w.bind(size=lambda ww, v: setattr(rect, 'size', ww.size))

    # ── Lifecycle ────────────────────────────────────────────
    def on_enter(self):
        Clock.schedule_interval(self._tick, 1)

    def on_leave(self):
        Clock.unschedule(self._tick)

    def start_new_game(self, difficulty='medium'):
        self._result_shown = False
        self.game = Game(difficulty)
        self._lbl_diff.text = difficulty.upper()
        self._apply_theme()
        self._update_board()

    # ── Theme ─────────────────────────────────────────────────
    def _change_theme(self, name):
        global active_theme
        active_theme = THEMES[name]
        self._apply_theme()
        self._update_board()

    def _apply_theme(self):
        t = active_theme
        self._root.canvas.before.clear()
        apply_bg(self._root, t['bg'])
        self._lbl_diff.color     = t['accent']
        self._lbl_time.color     = t['given_fg']
        self._lbl_mistakes.color = t['conflict_fg']
        self._btn_undo.color     = t['given_fg'];    self._btn_undo.background_color    = t['btn_bg']
        self._btn_pencil.color   = t['pencil_btn_fg'];self._btn_pencil.background_color = t['btn_bg']
        self._btn_new.color      = t['given_fg'];    self._btn_new.background_color     = t['btn_bg']
        self._btn_hint.color     = t['hint_fg'];     self._btn_hint.background_color    = t['btn_bg']
        self._btn_theme.color    = t['accent'];      self._btn_theme.background_color   = t['btn_bg']
        self._btn_del.color      = t['del_fg'];      self._btn_del.background_color     = t['del_bg']
        for btn in self._numpad_btns:
            btn.color = t['accent']
            btn.background_color = t['btn_bg']

    # ── Interactions ─────────────────────────────────────────
    def _on_cell(self, inst):
        if self.game:
            self.game.selected = (inst.row, inst.col)
            self._update_board()

    def _input(self, num):
        if not self.game:
            return
        result = self.game.input(num)
        if result == 'error':
            play_sound('error')
            do_haptic(0.08)
            self._shake_cell(*self.game.selected)
        elif result == 'correct':
            play_sound('correct')
            self._flash_cell(*self.game.selected, color=active_theme['flash_ok'])
        self._update_board()
        if self.game.won:
            self._win_animation()
        elif self.game.lost:
            self._show_result()

    def _undo(self, *_):
        if self.game and self.game.undo():
            self._update_board()

    def _toggle_pencil(self, *_):
        if not self.game:
            return
        self.game.pencil_mode = not self.game.pencil_mode
        t = active_theme
        if self.game.pencil_mode:
            self._btn_pencil.background_color = t['pencil_btn_fg']
            self._btn_pencil.color = t['bg']
        else:
            self._btn_pencil.background_color = t['btn_bg']
            self._btn_pencil.color = t['pencil_btn_fg']

    def _hint(self, *_):
        if not self.game:
            return
        self.game.hint()
        self._update_board()
        if self.game.won:
            self._win_animation()

    def _ask_new(self, *_):
        difficulty_popup(self._do_new)

    def _do_new(self, diff):
        self.start_new_game(diff)

    def _ask_restart(self):
        confirm_popup("Restart", "Restart this puzzle?", self._do_restart)

    def _do_restart(self):
        self._result_shown = False
        self.game.restart()
        self._update_board()

    def _go_menu(self):
        self.manager.current = 'menu'

    # ── Timer ────────────────────────────────────────────────
    def _tick(self, dt):
        if self.game and not self.game.won and not self.game.lost:
            m, s = divmod(self.game.elapsed(), 60)
            self._lbl_time.text     = f"{m:02d}:{s:02d}"
            self._lbl_mistakes.text = f"{self.game.mistakes}/{self.game.max_mistakes}"

    # ── Animations ───────────────────────────────────────────
    def _flash_cell(self, r, c, color):
        cell = self.cells[r][c]
        orig = tuple(cell.background_color)
        Animation(background_color=list(color), duration=0.08).start(cell)
        Clock.schedule_once(lambda dt: setattr(cell, 'background_color', orig), 0.18)

    def _shake_cell(self, r, c):
        cell = self.cells[r][c]
        orig_x = cell.x
        anim = (
            Animation(x=orig_x - dp(6), duration=0.04) +
            Animation(x=orig_x + dp(6), duration=0.04) +
            Animation(x=orig_x - dp(4), duration=0.04) +
            Animation(x=orig_x + dp(4), duration=0.04) +
            Animation(x=orig_x,         duration=0.04)
        )
        anim.start(cell)

    def _win_animation(self):
        """Light up cells in a wave, then show result popup."""
        play_sound('win')
        do_haptic(0.15)
        t = active_theme
        all_cells = [(r, c) for r in range(9) for c in range(9)]
        # Wave order: distance from top-left
        all_cells.sort(key=lambda rc: rc[0] + rc[1])
        def _light(idx, dt):
            if idx >= len(all_cells):
                self._show_result()
                return
            r, c = all_cells[idx]
            self._flash_cell(r, c, t['flash_ok'])
            Clock.schedule_once(lambda dt2, i=idx+1: _light(i, dt2), 0.03)
        Clock.schedule_once(lambda dt: _light(0, dt), 0.1)

    # ── Result popup ─────────────────────────────────────────
    def _show_result(self):
        if self._result_shown:
            return
        self._result_shown = True
        Clock.schedule_once(lambda dt: result_popup(
            won=self.game.won,
            elapsed=self.game.elapsed(),
            mistakes=self.game.mistakes,
            difficulty=self.game.difficulty,
            on_new=lambda: difficulty_popup(self._do_new),
            on_restart=self._ask_restart,
            on_menu=self._go_menu,
        ), 0.5)

    # ── Board rendering ──────────────────────────────────────
    def _update_board(self):
        if not self.game:
            return
        t = active_theme
        sel_r, sel_c = self.game.selected
        sel_val  = self.game.board[sel_r][sel_c]
        conflicts = self.game.conflicts()
        placed   = count_placed(self.game.board)

        # Dim numpad buttons for completed digits
        for i, btn in enumerate(self._numpad_btns, 1):
            if placed[i] >= 9:
                btn.color = [t['accent'][0], t['accent'][1], t['accent'][2], 0.25]
                btn.background_color = [t['btn_bg'][0], t['btn_bg'][1], t['btn_bg'][2], 0.4]
            else:
                btn.color = t['accent']
                btn.background_color = t['btn_bg']

        for r in range(9):
            for c in range(9):
                cell  = self.cells[r][c]
                v     = self.game.board[r][c]
                marks = self.game.pencils.get((r, c))
                is_given    = (r, c) in self.game.givens
                is_sel      = (r == sel_r and c == sel_c)
                is_conflict = (r, c) in conflicts
                in_rcb = (r == sel_r or c == sel_c or
                          (r//3 == sel_r//3 and c//3 == sel_c//3))
                is_same_num = (v != 0 and v == sel_val and not is_sel)

                # Reset
                cell.font_size = '26sp'
                cell.background_color = t['cell_bg']
                cell.color = t['given_fg']
                cell.text  = ''

                # Background priority: selected > same-num > row/col/box > conflict bg
                if is_sel:
                    cell.background_color = t['selected']
                elif is_same_num:
                    cell.background_color = t['same_num']
                elif in_rcb:
                    cell.background_color = t['highlight']

                # Text
                if v != 0:
                    cell.text = str(v)
                    if is_conflict:
                        cell.color = t['conflict_fg']
                    elif is_given:
                        cell.color = t['given_fg']
                    else:
                        cell.color = t['user_fg']
                elif marks:
                    cell.font_size = '10sp'
                    cell.text = ' '.join(str(m) for m in sorted(marks))
                    cell.color = t['pencil_fg'] if not is_sel else t['given_fg']

# ============================================================
# APP
# ============================================================

class SudokuApp(App):
    def build(self):
        self.title = "Sudoku"
        sm = ScreenManager(transition=FadeTransition(duration=0.2))
        sm.add_widget(MainMenuScreen(name='menu'))
        sm.add_widget(GameScreen(name='game'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.current = 'menu'
        return sm

if __name__ == '__main__':
    SudokuApp().run()