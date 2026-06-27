import os, sys


D = {"1", "true", "yes", "on", "y", "t", "enable", "enabled"}

if os.getenv("NOCOLOR", "").lower() not in D and os.getenv("OSENV_NOCOLOR", "").lower() not in D:
    RED     = "\033[31m"  # ANSI red
    GREEN   = "\033[32m"  # ANSI green
    YELLOW  = "\033[33m"  # ANSI yellow
    CYAN    = "\033[36m"  # ANSI cyan
    MAGENTA = "\033[35m"  # ANSI magenta
    GRAY    = "\033[90m"  # ANSI bright black (gray)
    NC      = "\033[0m"   # reset
    BOLD    = "\033[1m"   # bold
else:
    RED = GREEN = CYAN = MAGENTA = GRAY = YELLOW = NC = BOLD = ""


def enrich(s: str, file=sys.stdout, flush=True):
    print(
        s   .replace(r"\[\]"        , "\xff"    ) \
            .replace(r"\[RED]"      , RED       ) \
            .replace(r"\[GREEN]"    , GREEN     ) \
            .replace(r"\[YELLOW]"   , YELLOW    ) \
            .replace(r"\[CYAN]"     , CYAN      ) \
            .replace(r"\[MAGENTA]"  , MAGENTA   ) \
            .replace(r"\[GRAY]"     , GRAY      ) \
            .replace(r"\[NC]"       , NC        ) \
            .replace(r"\[BOLD]"     , BOLD      ) \
            .replace( "\xff"        , "\\"      ) \
        #
        ,   end=""
        ,   file=file
        ,   flush=flush
    )


def rich(*values, sep=" ", end="\n", file=sys.stdout, flush=True):
    enrich(
        sep.join(str(i) if not isinstance(i, str) else i for i in values) + end,
        file=file,
        flush=flush
    )


def e(*values, sep=" ", end="\n", file=sys.stdout, flush=True):
    rich( "\\[RED]\\[BOLD]ERR\\[NC]\\[BOLD]:\\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )


def w(*values, sep=" ", end="\n", file=sys.stdout, flush=True):
    rich( "\\[YELLOW]\\[BOLD]WRN\\[NC]\\[BOLD]:\\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )


def n(*values, sep=" ", end="\n", file=sys.stdout, flush=True):
    rich( "\\[CYAN]\\[BOLD]NOT\\[NC]\\[BOLD]:\\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )


def ii(*values, sep=" ", end="\n", file=sys.stdout, flush=True):
    rich( "\\[GREEN]\\[BOLD]INF\\[NC]\\[BOLD]:\\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )


def i(pref, *values, sep=" ", end="\n", file=sys.stdout, flush=True):
    rich( f"\\[GREEN]\\[BOLD]INF\\[NC]\\[BOLD]: {pref}: \\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )


def f(*values, sep=" ", end="\n", file=sys.stdout, flush=True, exit=1):
    rich( "\\[MAGENTA]\\[BOLD]FAT\\[NC]\\[BOLD]:\\[NC] ", *values, sep=sep, end=end, file=file, flush=flush )
    if exit: sys.exit(exit)


__all__ = list("ewnif") + ["rich", "ii"]
