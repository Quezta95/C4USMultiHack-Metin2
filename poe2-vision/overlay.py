"""Windows overlay that magnifies a user-selected part of the visible game window."""
import ctypes
from ctypes import wintypes
import math
import sys

from PIL import ImageGrab


def parse_region(text):
    """Parse x, y, width and height as percentages of the game client area."""
    try:
        values = tuple(float(part.strip()) for part in text.split(','))
    except ValueError as exc:
        raise ValueError('Podaj cztery liczby oddzielone przecinkami.') from exc
    if len(values) != 4 or not all(math.isfinite(value) for value in values):
        raise ValueError('Podaj cztery liczby oddzielone przecinkami.')
    x, y, width, height = values
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 100 or y + height > 100:
        raise ValueError('Obszar musi mieścić się w granicach 0–100%.')
    return values


def region_box(client_box, region):
    left, top, right, bottom = client_box
    x, y, width, height = region
    client_width, client_height = right - left, bottom - top
    if client_width <= 0 or client_height <= 0:
        raise ValueError('Okno gry ma zerowy rozmiar.')
    result = (left + round(client_width * x / 100), top + round(client_height * y / 100),
              left + round(client_width * (x + width) / 100),
              top + round(client_height * (y + height) / 100))
    if result[0] >= result[2] or result[1] >= result[3]:
        raise ValueError('Wybrany obszar jest zbyt mały.')
    return result


def overlaps(first, second):
    return first[0] < second[2] and first[2] > second[0] and first[1] < second[3] and first[3] > second[1]


class WindowsGame:
    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Nakładka wymaga systemu Windows.')
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user32.GetParent.argtypes = [wintypes.HWND]
        self.user32.GetParent.restype = wintypes.HWND
        self.user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]

    def active_client(self, title):
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        text = ctypes.create_unicode_buffer(self.user32.GetWindowTextLengthW(hwnd) + 1)
        self.user32.GetWindowTextW(hwnd, text, len(text))
        if title.casefold() not in text.value.casefold():
            return None
        rect = wintypes.RECT()
        point = wintypes.POINT(0, 0)
        if not self.user32.GetClientRect(hwnd, ctypes.byref(rect)) or not self.user32.ClientToScreen(hwnd, ctypes.byref(point)):
            return None
        return point.x, point.y, point.x + rect.right, point.y + rect.bottom

    def set_no_activate(self, window_id):
        hwnd = self.user32.GetParent(window_id) or window_id
        extended_style = -20
        flags = self.user32.GetWindowLongW(hwnd, extended_style)
        self.user32.SetWindowLongW(hwnd, extended_style, flags | 0x08000000 | 0x00000080)


def main():
    if sys.platform != 'win32':
        print('Nakładka wymaga Windows 11 oraz widocznego okna gry.', file=sys.stderr)
        return 1
    # Use physical pixel coordinates for the Windows API and screen capture.
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        user32.SetProcessDPIAware()
    import tkinter as tk
    from tkinter import ttk
    from PIL import ImageTk

    game = WindowsGame()
    root = tk.Tk()
    root.title('PoE 2 — ustawienia nakładki')
    root.geometry('510x290')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=18)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='Nakładka minimapy', font=('Segoe UI', 16, 'bold')).pack(anchor='w')
    ttk.Label(frame, text='Powiększa widoczny fragment obrazu gry.').pack(anchor='w', pady=(3, 12))
    region = tk.StringVar(value='84, 0, 16, 24')
    title = tk.StringVar(value='Path of Exile')
    status = tk.StringVar(value='Włącz nakładkę i przejdź do okna gry.')
    ttk.Label(frame, text='Obszar: x, y, szerokość, wysokość (% okna gry)').pack(anchor='w')
    ttk.Entry(frame, textvariable=region).pack(fill='x', pady=(2, 8))
    ttk.Label(frame, text='Fragment tytułu okna gry').pack(anchor='w')
    ttk.Entry(frame, textvariable=title).pack(fill='x', pady=(2, 10))
    ttk.Label(frame, textvariable=status, wraplength=470).pack(anchor='w', pady=4)
    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)
    overlay.attributes('-topmost', True)
    overlay.withdraw()
    bar = tk.Frame(overlay, bg='#1a1c1f')
    bar.pack(fill='x')
    label = tk.Label(bar, text='◈  MINIMAPA  ·  przeciągnij', fg='#d7ad70', bg='#1a1c1f', font=('Segoe UI', 9))
    label.pack(side='left', padx=8, pady=5)
    picture = tk.Label(overlay, bg='#101113')
    picture.pack()
    state = {'running': False, 'placed': False, 'shown': False, 'photo': None, 'drag': None, 'generation': 0}

    def move_start(event):
        state['drag'] = (event.x_root - overlay.winfo_x(), event.y_root - overlay.winfo_y())

    def move(event):
        if state['drag']:
            overlay.geometry(f'{event.x_root - state["drag"][0]:+d}{event.y_root - state["drag"][1]:+d}')

    for widget in (bar, label):
        widget.bind('<ButtonPress-1>', move_start)
        widget.bind('<B1-Motion>', move)

    def hide():
        if state['shown']:
            overlay.withdraw()
            state['shown'] = False

    def tick(generation):
        if not state['running'] or generation != state['generation']:
            return
        try:
            client = game.active_client(title.get().strip()) if title.get().strip() else None
            if client is None:
                hide()
                status.set('Oczekiwanie na aktywne okno gry.')
            else:
                box = region_box(client, parse_region(region.get()))
                if not state['placed']:
                    overlay.geometry(f'{client[0] + 20:+d}{client[1] + 50:+d}')
                    state['placed'] = True
                overlay_box = (overlay.winfo_x(), overlay.winfo_y(), overlay.winfo_x() + overlay.winfo_width(), overlay.winfo_y() + overlay.winfo_height())
                if state['shown'] and overlaps(box, overlay_box):
                    hide()
                    state['running'] = False
                    state['placed'] = False
                    button.configure(text='Włącz nakładkę')
                    status.set('Nakładka zasłaniała źródło. Zmień obszar lub uruchom ją ponownie.')
                else:
                    image = ImageGrab.grab(bbox=box, all_screens=True)
                    scale = min(320 / image.width, 600 / image.height)
                    image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))))
                    state['photo'] = ImageTk.PhotoImage(image)
                    picture.configure(image=state['photo'])
                    if not state['shown']:
                        overlay.update_idletasks()
                        game.set_no_activate(overlay.winfo_id())
                        overlay.deiconify()
                        state['shown'] = True
                    status.set('Nakładka aktywna. Źródło: widoczny fragment ekranu gry.')
        except (ValueError, OSError, RuntimeError) as exc:
            hide()
            status.set(str(exc))
        if state['running']:
            root.after(250, lambda: tick(generation))

    def toggle():
        if state['running']:
            state['running'] = False
            state['generation'] += 1
            hide()
            button.configure(text='Włącz nakładkę')
            status.set('Nakładka wyłączona.')
            return
        try:
            parse_region(region.get())
            if not title.get().strip():
                raise ValueError('Podaj fragment tytułu okna gry.')
        except ValueError as exc:
            status.set(str(exc))
            return
        state['running'] = True
        state['generation'] += 1
        button.configure(text='Wyłącz nakładkę')
        tick(state['generation'])

    button = ttk.Button(frame, text='Włącz nakładkę', command=toggle)
    button.pack(anchor='w', pady=6)
    root.mainloop()
    return 0


if __name__ == '__main__':
    sys.exit(main())
