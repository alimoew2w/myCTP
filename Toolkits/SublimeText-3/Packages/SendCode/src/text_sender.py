import sublime
import re
from .settings import Settings
from .terminal import send_to_terminal
from .iterm import send_to_iterm
from .r import send_to_r
from .rstudio import send_to_rstudio
from .conemu import send_to_conemu, send_to_cmder
from .tmux import send_to_tmux
from .screen import send_to_screen
from .chrome import send_to_chrome_jupyter, send_to_chrome_rstudio
from .safari import send_to_safari_jupyter, send_to_safari_rstudio
from .sublimerepl import send_to_sublimerepl


class TextSender:

    def __init__(self, view, cmd=None, prog=None):
        self.view = view
        self.settings = Settings(view)
        if prog:
            self.prog = prog
        else:
            self.prog = self.settings.get("prog")
        self.bracketed_paste_mode = self.settings.get("bracketed_paste_mode")

    @classmethod
    def initialize(cls, view, **kwargs):
        syntax = Settings(view).syntax()
        if syntax == "r":
            return RTextSender(view, **kwargs)
        elif syntax == "python":
            return PythonTextSender(view, **kwargs)
        elif syntax == "julia":
            return JuliaTextSender(view, **kwargs)
        else:
            return TextSender(view, **kwargs)

    def send_to_terminal(self, cmd):
        send_to_terminal(cmd, bracketed=self.bracketed_paste_mode)

    def send_to_iterm(self, cmd):
        send_to_iterm(cmd, bracketed=self.bracketed_paste_mode)

    def send_to_conemu(self, cmd):
        conemuc = self.settings.get("conemuc")
        send_to_conemu(cmd, conemuc, bracketed=self.bracketed_paste_mode)

    def send_to_cmder(self, cmd):
        conemuc = self.settings.get("conemuc")
        send_to_cmder(cmd, conemuc, bracketed=self.bracketed_paste_mode)

    def send_to_tmux(self, cmd):
        tmux = self.settings.get("tmux", "tmux")
        send_to_tmux(cmd, tmux, bracketed=self.bracketed_paste_mode)

    def send_to_screen(self, cmd):
        screen = self.settings.get("screen", "screen")
        send_to_screen(cmd, screen, bracketed=self.bracketed_paste_mode)

    def send_to_chrome_jupyter(self, cmd):
        send_to_chrome_jupyter(cmd)

    def send_to_safari_jupyter(self, cmd):
        send_to_safari_jupyter(cmd)

    def send_to_sublimerepl(self, cmd):
        send_to_sublimerepl(cmd)

    def send_text(self, cmd):
        cmd = cmd.rstrip()
        cmd = cmd.expandtabs(self.view.settings().get("tab_size", 4))
        prog = self.prog.lower()
        if prog == "terminal":
            self.send_to_terminal(cmd)
        elif prog == "iterm":
            self.send_to_iterm(cmd)
        elif prog == "cmder":
            self.send_to_cmder(cmd)
        elif prog == "conemu":
            self.send_to_conemu(cmd)
        elif prog == "tmux":
            self.send_to_tmux(cmd)
        elif prog == "screen":
            self.send_to_screen(cmd)
        elif prog == "chrome-jupyter":
            self.send_to_chrome_jupyter(cmd)
        elif prog == "safari-jupyter":
            self.send_to_safari_jupyter(cmd)
        elif prog == "sublimerepl":
            self.send_to_sublimerepl(cmd)
        else:
            sublime.message_dialog("%s is not supported for current syntax." % prog)


class RTextSender(TextSender):

    def send_text(self, cmd):
        cmd = cmd.rstrip()
        cmd = cmd.expandtabs(self.view.settings().get("tab_size", 4))
        prog = self.prog.lower()
        if prog == "r":
            self.send_to_r(cmd)
        elif prog == "rstudio":
            self.send_to_rstudio(cmd)
        elif prog == "chrome-rstudio":
            self.send_to_chrome_rstudio(cmd)
        elif prog == "safari-rstudio":
            self.send_to_safari_rstudio(cmd)
        else:
            super(RTextSender, self).send_text(cmd)

    def send_to_r(self, cmd):
        send_to_r(cmd)

    def send_to_rstudio(self, cmd):
        send_to_rstudio(cmd)

    def send_to_chrome_rstudio(self, cmd):
        send_to_chrome_rstudio(cmd)

    def send_to_safari_rstudio(self, cmd):
        send_to_safari_rstudio(cmd)


class PythonTextSender(TextSender):

    def send_to_terminal(self, cmd):
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_terminal(cmd, bracketed=True)
                send_to_terminal("", bracketed=False)
            else:
                send_to_terminal(r"%cpaste -q")
                send_to_terminal(cmd)
                send_to_terminal("--")
        else:
            send_to_terminal(cmd)

    def send_to_iterm(self, cmd):
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_iterm(cmd, bracketed=True)
                send_to_iterm("", bracketed=False)
            else:
                send_to_iterm(r"%cpaste -q")
                send_to_iterm(cmd)
                send_to_iterm("--")
        else:
            send_to_iterm(cmd)

    def send_to_conemu(self, cmd):
        conemuc = self.settings.get("conemuc")
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_conemu(cmd, conemuc, bracketed=False)
                send_to_conemu("", conemuc, bracketed=False)
            else:
                send_to_conemu(r"%cpaste -q", conemuc)
                send_to_conemu(cmd, conemuc)
                send_to_conemu("--", conemuc)
        else:
            send_to_conemu(cmd, conemuc)

    def send_to_cmder(self, cmd):
        conemuc = self.settings.get("conemuc")
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_cmder(cmd, conemuc, bracketed=False)
                send_to_cmder("", conemuc, bracketed=False)
            else:
                send_to_cmder(r"%cpaste -q", conemuc)
                send_to_cmder(cmd, conemuc)
                send_to_cmder("--", conemuc)
        else:
            send_to_cmder(cmd, conemuc)

    def send_to_tmux(self, cmd):
        tmux = self.settings.get("tmux", "tmux")
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_tmux(cmd, tmux, bracketed=True)
                send_to_tmux("", tmux, bracketed=False)
            else:
                send_to_tmux(r"%cpaste -q", tmux)
                send_to_tmux(cmd, tmux)
                # send ctrl-D instead of "--" since `set-buffer` does not work properly
                send_to_tmux("\x04", tmux)
        else:
            send_to_tmux(cmd, tmux)

    def send_to_screen(self, cmd):
        screen = self.settings.get("screen", "screen")
        if len(re.findall("\n", cmd)) > 0:
            if self.bracketed_paste_mode:
                send_to_screen(cmd, screen, bracketed=True)
                send_to_screen("", screen, bracketed=False)
            else:
                send_to_screen(r"%cpaste -q", screen)
                send_to_screen(cmd, screen)
                send_to_screen("--", screen)
        else:
            send_to_screen(cmd, screen)


class JuliaTextSender(TextSender):

    pass
