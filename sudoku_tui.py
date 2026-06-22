#!/usr/bin/env python3
"""
sudoku-tui — A terminal Sudoku game 
"""
import curses
import random
import time
from curses import wrapper

# ============================================================
# Sudoku Logic
# ============================================================

def generate_solution():
    base = 3
    side = base * base
    def pattern(r, c):
        return (base * (r % base) + r // base + c) % side
    rB = range(base)
    rows = [g*base + r for g in random.sample(rB, base) for r in random.sample(rB, base)]
    cols = [g*base + c for g in random.sample(rB, base) for c in random.sample(rB, base)]
    nums = random.sample(range(1, side + 1), side)
    return [[nums[pattern(r, c)] for c in cols] for r in rows]


def make_puzzle(solution, difficulty):
    puzzle = [row[:] for row in solution]
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)
    removals = {'easy': 38, 'medium': 46, 'hard': 52, 'expert': 56}[difficulty]
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
                if i != c and board[r][i] == v:
                    bad = True
                if i != r and board[i][c] == v:
                    bad = True
            if not bad:
                br, bc = (r // 3) * 3, (c // 3) * 3
                for i in range(3):
                    for j in range(3):
                        if (br + i, bc + j) != (r, c) and board[br + i][bc + j] == v:
                            bad = True
            if bad:
                cf.add((r, c))
    return cf


def is_complete(board):
    if any(board[r][c] == 0 for r in range(9) for c in range(9)):
        return False
    return not find_conflicts(board)


# ============================================================
# Game State
# ============================================================

DIFFICULTIES = ['easy', 'medium', 'hard', 'expert']


class Game:
    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty
        self.solution = generate_solution()
        self.puzzle = make_puzzle(self.solution, difficulty)
        self.board = [row[:] for row in self.puzzle]
        self.givens = {(r, c) for r in range(9) for c in range(9) if self.puzzle[r][c] != 0}
        self.pencils = {}
        self.selected = (4, 4)
        self.pencil_mode = False
        self.start_time = time.time()
        self.mistakes = 0
        self.max_mistakes = 5
        self.won = False
        self.lost = False
        self.hints_used = 0
        self.message = ''
        self.message_until = 0

    def flash(self, msg, dur=2.0):
        self.message = msg
        self.message_until = time.time() + dur

    def current_message(self):
        return self.message if time.time() < self.message_until else ''

    def move(self, dr, dc):
        if self.won or self.lost:
            return
        r, c = self.selected
        self.selected = ((r + dr) % 9, (c + dc) % 9)

    def input(self, num):
        if self.won or self.lost:
            return
        r, c = self.selected
        if (r, c) in self.givens:
            self.flash("Can't modify clue")
            return
        if self.pencil_mode:
            if num == 0:
                self.pencils.pop((r, c), None)
            elif self.board[r][c] != 0:
                self.flash("Cell occupied — clear first")
            else:
                marks = self.pencils.setdefault((r, c), set())
                if num in marks:
                    marks.discard(num)
                    if not marks:
                        self.pencils.pop((r, c))
                else:
                    marks.add(num)
        else:
            if num == 0:
                self.board[r][c] = 0
                self.pencils.pop((r, c), None)
            else:
                if self.board[r][c] == num:
                    return
                self.board[r][c] = num
                self.pencils.pop((r, c), None)
                if self.solution[r][c] != num:
                    self.mistakes += 1
                    if self.mistakes >= self.max_mistakes:
                        self.lost = True
                        self.flash("GAME OVER — too many mistakes", 1e9)
                    else:
                        self.flash(f"Wrong! Mistakes {self.mistakes}/{self.max_mistakes}")
                else:
                    for i in range(9):
                        if (r, i) in self.pencils:
                            self.pencils[(r, i)].discard(num)
                        if (i, c) in self.pencils:
                            self.pencils[(i, c)].discard(num)
                    br, bc = (r // 3) * 3, (c // 3) * 3
                    for i in range(3):
                        for j in range(3):
                            if (br + i, bc + j) in self.pencils:
                                self.pencils[(br + i, bc + j)].discard(num)
                    if is_complete(self.board):
                        self.won = True
                        self.flash("SOLVED! Press n for new, q to quit", 1e9)

    def hint(self):
        if self.won or self.lost:
            return
        r, c = self.selected
        if (r, c) in self.givens or self.board[r][c] == self.solution[r][c]:
            empties = [(i, j) for i in range(9) for j in range(9)
                       if self.board[i][j] == 0 or self.board[i][j] != self.solution[i][j]]
            if not empties:
                return
            r, c = random.choice(empties)
            self.selected = (r, c)
        self.board[r][c] = self.solution[r][c]
        self.pencils.pop((r, c), None)
        self.hints_used += 1
        self.flash(f"Hint: {self.solution[r][c]} at R{r+1}C{c+1}")
        if is_complete(self.board):
            self.won = True
            self.flash("SOLVED (with hints)!", 1e9)

    def check(self):
        conflicts = find_conflicts(self.board)
        filled = sum(1 for r in range(9) for c in range(9) if self.board[r][c] != 0)
        if conflicts:
            self.flash(f"{len(conflicts)} conflict(s) — {filled}/81 filled")
        else:
            self.flash(f"No conflicts — {filled}/81 filled")

    def restart(self):
        self.board = [row[:] for row in self.puzzle]
        self.pencils = {}
        self.mistakes = 0
        self.hints_used = 0
        self.start_time = time.time()
        self.won = False
        self.lost = False
        self.flash("Restarted")

    def elapsed(self):
        return int(time.time() - self.start_time)


# ============================================================
# Colors — FIXED for dark terminals
# ============================================================

C_BORDER = 1;  C_TITLE = 2;  C_GIVEN = 3;  C_USER = 4;  C_PENCIL = 5
C_ERROR = 6;   C_SELECTED = 7; C_HL_NUM = 8; C_FOOTER = 9; C_HEADER = 10
C_OK = 11;     C_DIM = 12;   C_ACCENT = 13; C_PANEL = 14; C_WARN = 15; C_RCB = 16
C_EMPTY = 17;  C_INFO_LABEL = 18


def init_colors():
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1
    except curses.error:
        bg = curses.COLOR_BLACK

    # Use bright/bold colors for better visibility on dark themes
    # Borders: bright cyan
    curses.init_pair(C_BORDER,   curses.COLOR_CYAN,    bg)
    # Title: bright cyan on black (forced bg for contrast)
    curses.init_pair(C_TITLE,    curses.COLOR_CYAN,    curses.COLOR_BLACK)
    # Givens: bright white (bold will be applied)
    curses.init_pair(C_GIVEN,    curses.COLOR_WHITE,   bg)
    # User entries: bright green
    curses.init_pair(C_USER,     curses.COLOR_GREEN,   bg)
    # Pencil marks: bright yellow
    curses.init_pair(C_PENCIL,   curses.COLOR_YELLOW,  bg)
    # Errors: bright red
    curses.init_pair(C_ERROR,    curses.COLOR_RED,     bg)
    # Selected cell: black on bright cyan
    curses.init_pair(C_SELECTED, curses.COLOR_BLACK,   curses.COLOR_CYAN)
    # Same-number highlight: bright white on blue
    curses.init_pair(C_HL_NUM,   curses.COLOR_WHITE,   curses.COLOR_BLUE)
    # Footer: black on bright cyan
    curses.init_pair(C_FOOTER,   curses.COLOR_BLACK,   curses.COLOR_CYAN)
    # Header: bright cyan on black
    curses.init_pair(C_HEADER,   curses.COLOR_CYAN,    curses.COLOR_BLACK)
    # OK/success: bright green
    curses.init_pair(C_OK,       curses.COLOR_GREEN,   bg)
    # Dim text — use bright black (gray) instead of dim white
    curses.init_pair(C_DIM,      curses.COLOR_CYAN,    bg)
    # Accent: bright magenta
    curses.init_pair(C_ACCENT,   curses.COLOR_MAGENTA, bg)
    # Panel labels: bright cyan
    curses.init_pair(C_PANEL,    curses.COLOR_CYAN,    bg)
    # Warning: bright yellow
    curses.init_pair(C_WARN,     curses.COLOR_YELLOW,  bg)
    # Row/col/box highlight — use a visible background (bright blue dimmed)
    # Instead of dark gray (invisible), use a dark blue that's visible
    try:
        if curses.COLORS >= 256:
            # Use color 17 (very dark blue) — visible on black
            curses.init_pair(C_RCB, curses.COLOR_WHITE, 17)
        else:
            curses.init_pair(C_RCB, curses.COLOR_WHITE, curses.COLOR_BLUE)
    except curses.error:
        curses.init_pair(C_RCB, curses.COLOR_WHITE, curses.COLOR_BLUE)
    # Empty cell dots — use a visible dim cyan (not dim white)
    curses.init_pair(C_EMPTY, curses.COLOR_CYAN, bg)
    # Info panel labels — bright cyan
    curses.init_pair(C_INFO_LABEL, curses.COLOR_CYAN, bg)


def CP(n):
    return curses.color_pair(n)


# ============================================================
# Box-drawing constants
# ============================================================

GRID_W = 37
GRID_H = 19

TOP_BORDER    = "┏━━━┯━━━┯━━━┳━━━┯━━━┯━━━┳━━━┯━━━┯━━━┓"
ROW_SEP_LIGHT = "┠───┼───┼───╂───┼───┼───╂───┼───┼───┨"
ROW_SEP_HEAVY = "┣━━━┿━━━┿━━━╋━━━┿━━━┿━━━╋━━━┿━━━┿━━━┫"
BOTTOM_BORDER = "┗━━━┷━━━┷━━━┻━━━┷━━━┷━━━┻━━━┷━━━┷━━━┛"


# ============================================================
# Helpers
# ============================================================

def fmt_time(s):
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def safe_addstr(stdscr, y, x, s, attr=curses.A_NORMAL):
    h, w = stdscr.getmaxyx()
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    try:
        stdscr.addstr(y, x, s[:max(0, w - x)], attr)
    except curses.error:
        pass


def draw_box(stdscr, y, x, h, w, title='', attr=None):
    if attr is None:
        attr = CP(C_BORDER)
    if h < 2 or w < 2:
        return
    safe_addstr(stdscr, y, x, '┌' + '─' * (w - 2) + '┐', attr)
    safe_addstr(stdscr, y + h - 1, x, '└' + '─' * (w - 2) + '┘', attr)
    for i in range(1, h - 1):
        safe_addstr(stdscr, y + i, x, '│', attr)
        safe_addstr(stdscr, y + i, x + w - 1, '│', attr)
    if title:
        t = f' {title} '
        safe_addstr(stdscr, y, x + 2, t, attr | curses.A_BOLD)


# ============================================================
# Rendering
# ============================================================

def draw_header(stdscr, game, y, w):
    bar = ' ' * w
    safe_addstr(stdscr, y, 0, bar, CP(C_HEADER))
    safe_addstr(stdscr, y + 1, 0, '─' * w, CP(C_BORDER) | curses.A_BOLD)

    title = " SUDOKU-TUI "
    safe_addstr(stdscr, y, 2, title, CP(C_TITLE) | curses.A_BOLD)

    diff_col = {'easy': C_OK, 'medium': C_USER,
                'hard': C_WARN, 'expert': C_ERROR}.get(game.difficulty, C_DIM)
    diff_str = f"[{game.difficulty.upper()}]"
    safe_addstr(stdscr, y, 2 + len(title), diff_str, CP(diff_col) | curses.A_BOLD)

    t = fmt_time(game.elapsed())
    parts = []
    if game.won:
        parts.append(("[SOLVED]", CP(C_OK) | curses.A_BOLD))
    elif game.lost:
        parts.append(("[GAME OVER]", CP(C_ERROR) | curses.A_BOLD))
    parts.append((f"Time {t}", CP(C_TITLE) | curses.A_BOLD))
    mc = C_WARN if game.mistakes else C_OK
    parts.append((f"Mistakes {game.mistakes}/{game.max_mistakes}",
                  CP(mc) | curses.A_BOLD))

    sep = "  "
    total = sum(len(s) for s, _ in parts) + len(sep) * (len(parts) - 1)
    right = w - 2 - total
    for i, (s, a) in enumerate(parts):
        safe_addstr(stdscr, y, right, s, a)
        right += len(s)
        if i < len(parts) - 1:
            right += len(sep)


def draw_grid(stdscr, game, gy, gx):
    # Borders — bold for better visibility
    safe_addstr(stdscr, gy + 0,  gx, TOP_BORDER,    CP(C_BORDER) | curses.A_BOLD)
    safe_addstr(stdscr, gy + 18, gx, BOTTOM_BORDER, CP(C_BORDER) | curses.A_BOLD)
    for r in range(1, 9):
        y = gy + 2 * r
        s = ROW_SEP_HEAVY if r % 3 == 0 else ROW_SEP_LIGHT
        safe_addstr(stdscr, y, gx, s, CP(C_BORDER) | curses.A_BOLD)

    sel = game.selected
    sel_val = game.board[sel[0]][sel[1]]
    conflicts = find_conflicts(game.board)

    for r in range(9):
        y = gy + 1 + 2 * r
        safe_addstr(stdscr, y, gx, '┃', CP(C_BORDER) | curses.A_BOLD)
        for c in range(9):
            cx = gx + 1 + 4 * c
            v = game.board[r][c]
            is_given = (r, c) in game.givens
            is_sel = (sel == (r, c))
            is_conflict = (r, c) in conflicts
            in_rcb = (r == sel[0] or c == sel[1] or
                      (r // 3 == sel[0] // 3 and c // 3 == sel[1] // 3))
            is_same_num = (v != 0 and v == sel_val and not is_sel)
            marks = game.pencils.get((r, c))

            if v != 0:
                content = f' {v} '
            elif marks:
                s = ''.join(str(m) for m in sorted(marks))
                content = s[:3].ljust(3)
            else:
                content = ' · '

            if is_sel:
                attr = CP(C_SELECTED) | curses.A_BOLD
            elif is_same_num:
                attr = CP(C_HL_NUM) | curses.A_BOLD
            elif is_conflict:
                attr = CP(C_ERROR) | curses.A_BOLD
            elif is_given:
                attr = CP(C_GIVEN) | curses.A_BOLD
            elif v != 0:
                attr = CP(C_USER) | curses.A_BOLD
            elif marks:
                attr = CP(C_PENCIL) | curses.A_BOLD  # Removed A_DIM
            elif in_rcb:
                attr = CP(C_RCB)
            else:
                # Empty cells — use C_EMPTY (visible cyan) instead of dim
                attr = CP(C_EMPTY)

            safe_addstr(stdscr, y, cx, content, attr)

            sep_x = gx + 4 + 4 * c
            sep_char = '┃' if (c == 8 or c % 3 == 2) else '│'
            safe_addstr(stdscr, y, sep_x, sep_char, CP(C_BORDER) | curses.A_BOLD)


def draw_side_panel(stdscr, game, py, px, pw, ph):
    draw_box(stdscr, py, px, ph, pw, title='INFO')
    y = py + 1
    x = px + 2
    label_w = 11

    def row(label, value, value_attr):
        nonlocal y
        # Labels use bright cyan (visible)
        safe_addstr(stdscr, y, x, label.ljust(label_w), CP(C_INFO_LABEL))
        safe_addstr(stdscr, y, x + label_w, value, value_attr)
        y += 1

    diff_col = {'easy': C_OK, 'medium': C_USER,
                'hard': C_WARN, 'expert': C_ERROR}.get(game.difficulty, C_DIM)
    row("Difficulty", game.difficulty.upper(), CP(diff_col) | curses.A_BOLD)
    row("Time", fmt_time(game.elapsed()), CP(C_ACCENT) | curses.A_BOLD)
    mc = C_OK if game.mistakes == 0 else (C_WARN if game.mistakes < game.max_mistakes else C_ERROR)
    row("Mistakes", f"{game.mistakes}/{game.max_mistakes}", CP(mc) | curses.A_BOLD)
    filled = sum(1 for r in range(9) for c in range(9) if game.board[r][c] != 0)
    row("Filled", f"{filled}/81", CP(C_USER) | curses.A_BOLD)
    row("Hints", str(game.hints_used), CP(C_ACCENT) | curses.A_BOLD)
    pm_attr = CP(C_PENCIL) | curses.A_BOLD if game.pencil_mode else CP(C_DIM)
    row("Pencil", "ON" if game.pencil_mode else "OFF", pm_attr)
    r, c = game.selected
    row("Cursor", f"R{r+1} C{c+1}", CP(C_DIM) | curses.A_BOLD)

    y += 1
    safe_addstr(stdscr, y, x, "LEGEND", CP(C_PANEL) | curses.A_BOLD)
    y += 1
    legend = [
        ("Given",    CP(C_GIVEN)    | curses.A_BOLD),
        ("User",     CP(C_USER)     | curses.A_BOLD),
        ("Pencil",   CP(C_PENCIL)   | curses.A_BOLD),
        ("Conflict", CP(C_ERROR)    | curses.A_BOLD),
        ("Cursor",   CP(C_SELECTED) | curses.A_BOLD),
        ("Same #",   CP(C_HL_NUM)   | curses.A_BOLD),
    ]
    for label, attr in legend:
        safe_addstr(stdscr, y, x,     " 5 ", attr)
        safe_addstr(stdscr, y, x + 4, label, CP(C_INFO_LABEL))
        y += 1

    msg = game.current_message()
    if msg and y < py + ph - 2:
        y += 1
        safe_addstr(stdscr, y, x, "STATUS", CP(C_PANEL) | curses.A_BOLD)
        y += 1
        max_w = pw - 4
        words = msg.split()
        line = ''
        for wd in words:
            test = (line + ' ' + wd).strip()
            if len(test) > max_w:
                safe_addstr(stdscr, y, x, line, CP(C_WARN) | curses.A_BOLD)
                y += 1
                line = wd
                if y >= py + ph - 1:
                    break
            else:
                line = test
        if line and y < py + ph:
            safe_addstr(stdscr, y, x, line, CP(C_WARN) | curses.A_BOLD)


def draw_footer(stdscr, y, w):
    keys = [
        ("hjkl/Arrows", "Move"),
        ("1-9",  "Place"),
        ("0/Del", "Clear"),
        ("Space", "Pencil"),
        ("n",    "New"),
        ("d",    "Diff"),
        ("r",    "Restart"),
        ("c",    "Check"),
        ("H",    "Hint"),
        ("q",    "Quit"),
    ]
    s = "  ".join(f"{k}:{v}" for k, v in keys)
    s = " " + s
    safe_addstr(stdscr, y, 0, ' ' * w, CP(C_FOOTER))
    safe_addstr(stdscr, y, 0, s[:w], CP(C_FOOTER) | curses.A_BOLD)


def draw_too_small(stdscr, msg):
    h, w = stdscr.getmaxyx()
    safe_addstr(stdscr, h // 2, max(0, (w - len(msg)) // 2),
                msg, CP(C_ERROR) | curses.A_BOLD)


# ============================================================
# Main loop
# ============================================================

def main(stdscr):
    init_colors()
    curses.curs_set(0)
    stdscr.timeout(500)
    stdscr.keypad(True)

    game = Game('medium')

    while True:
        stdscr.erase()
        h, w = stdscr.getmaxyx()

        side_w = 26
        total_w = GRID_W + 2 + side_w
        min_w = total_w + 2
        min_h = GRID_H + 4

        if w < min_w or h < min_h:
            draw_too_small(stdscr,
                f"Terminal too small. Need {min_w}x{min_h}, have {w}x{h}. Press q to quit.")
            stdscr.refresh()
            key = stdscr.getch()
            if key in (ord('q'), 27):
                break
            continue

        draw_header(stdscr, game, 0, w)

        start_x = max(2, (w - total_w) // 2)
        grid_x = start_x
        grid_y = 3
        panel_x = start_x + GRID_W + 2

        draw_grid(stdscr, game, grid_y, grid_x)
        draw_side_panel(stdscr, game, grid_y, panel_x, side_w, GRID_H)

        draw_footer(stdscr, h - 1, w)

        if game.won or game.lost:
            if game.won:
                msg = "  PUZZLE SOLVED  "
                attr = CP(C_OK) | curses.A_BOLD
            else:
                msg = "  GAME OVER  "
                attr = CP(C_ERROR) | curses.A_BOLD
            my = grid_y + GRID_H // 2
            mx = grid_x + (GRID_W - len(msg)) // 2
            safe_addstr(stdscr, my, mx, ' ' * len(msg), attr)
            safe_addstr(stdscr, my, mx, msg, attr)
            sub = "Press n for new game, q to quit"
            safe_addstr(stdscr, my + 2, grid_x + (GRID_W - len(sub)) // 2,
                        sub, CP(C_WARN) | curses.A_BOLD)

        stdscr.refresh()

        key = stdscr.getch()
        if key == -1:
            continue

        if key in (ord('q'), 27):
            break
        elif key in (curses.KEY_UP, ord('k')):
            game.move(-1, 0)
        elif key in (curses.KEY_DOWN, ord('j')):
            game.move(1, 0)
        elif key in (curses.KEY_LEFT, ord('h')):
            game.move(0, -1)
        elif key in (curses.KEY_RIGHT, ord('l')):
            game.move(0, 1)
        elif ord('1') <= key <= ord('9'):
            game.input(key - ord('0'))
        elif key in (ord('0'), curses.KEY_DC, 8, 127, curses.KEY_BACKSPACE):
            game.input(0)
        elif key == ord(' '):
            game.pencil_mode = not game.pencil_mode
            game.flash(f"Pencil mode {'ON' if game.pencil_mode else 'OFF'}")
        elif key == ord('n'):
            idx = (DIFFICULTIES.index(game.difficulty) + 1) % len(DIFFICULTIES)
            game = Game(DIFFICULTIES[idx])
        elif key == ord('N'):
            game = Game(game.difficulty)
        elif key == ord('d'):
            idx = (DIFFICULTIES.index(game.difficulty) + 1) % len(DIFFICULTIES)
            game.flash(f"Next difficulty: {DIFFICULTIES[idx].upper()} (press n)")
        elif key == ord('r'):
            game.restart()
        elif key == ord('c'):
            game.check()
        elif key == ord('H'):
            game.hint()


if __name__ == '__main__':
    wrapper(main)
