import subprocess


def _send_to_tmux(cmd, tmux):
    n = 200
    chunks = [cmd[i:i+n] for i in range(0, len(cmd), n)]
    for chunk in chunks:
        subprocess.check_call([tmux, 'set-buffer', '--', chunk])
        subprocess.check_call([tmux, 'paste-buffer', '-d'])


def send_to_tmux(cmd, tmux="tmux", bracketed=False):
    if bracketed:
        subprocess.check_call([tmux, 'set-buffer', "\x1b[200~"])
        subprocess.check_call([tmux, 'paste-buffer', '-d'])
        _send_to_tmux(cmd, tmux)
        subprocess.check_call([tmux, 'set-buffer', "\x1b[201~"])
        subprocess.check_call([tmux, 'paste-buffer', '-d'])
        _send_to_tmux("\n", tmux)
    else:
        if cmd != "\x04":
            cmd = cmd + "\n"
        _send_to_tmux(cmd, tmux)
