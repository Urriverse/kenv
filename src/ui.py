import sys
import termios
import tty
from utils import GREEN, BOLD, NC, CLEAR, INVERSE 


def interactive_select(profiles: dict) -> str:
    names = list(profiles.keys())
    idx = 0

    def draw():
        lines = [
            CLEAR,
            "\r\n\r\n\r\n",
            f"  {GREEN}Select kernel build profile:{NC}\r\n",
            "\r\n",
        ]
        for i, name in enumerate(names):
            desc = profiles[name].get("profile", {}).get("description", "").strip()
            if i == idx:
                prefix = f"  {INVERSE}>"
                name_str = f"{BOLD}{name:<12}{NC}"
            else:
                prefix = "   "
                name_str = f"{name:<12}"
            lines.append(f"{prefix} {name_str}  {desc}\r\n")
        lines.append("\r\n  ↑/↓: navigate   Enter: confirm   Q: quit\r\n")
        sys.stdout.write("".join(lines))
        sys.stdout.flush()

    class RawTerminal:
        def __enter__(self):
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setraw(self.fd)
            return self

        def __exit__(self, *args):
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

        def get_key(self) -> str:
            c = sys.stdin.read(1)
            if c == '\x1b':  # Escape sequence
                n = sys.stdin.read(1)
                if n == '[':
                    m = sys.stdin.read(1)
                    if m == 'A': return 'UP'
                    if m == 'B': return 'DOWN'
                    if m == 'C': return 'RIGHT'
                    if m == 'D': return 'LEFT'
                return c
            if c in ('\r', '\n'):
                return 'ENTER'
            return c

    try:
        with RawTerminal() as term:
            draw()
            while True:
                key = term.get_key()
                if key == 'UP':
                    idx = (idx - 1) % len(names)
                    draw()
                elif key == 'DOWN':
                    idx = (idx + 1) % len(names)
                    draw()
                elif key == 'ENTER':
                    break
                elif key.lower() == 'q':
                    sys.stdout.write(CLEAR + "Aborted.\r\n")
                    sys.stdout.flush()
                    sys.exit(130)
    except Exception:
        sys.stdout.write("\r\n")
        raise

    return names[idx]
