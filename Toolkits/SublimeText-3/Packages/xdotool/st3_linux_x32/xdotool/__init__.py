import subprocess
import os


XDOTOOL = os.path.join(os.path.dirname(__file__), "xdotool")
os.chmod(XDOTOOL, 0o700)


def xdotool(*args):
    return subprocess.check_output([XDOTOOL] + list(args))
