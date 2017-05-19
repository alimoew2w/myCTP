# xdotool for Sublime Text

This is a Package Control dependency providing
[xdotool](https://github.com/jordansissel/xdotool) binary, a tool
to fake keyboard/mouse input and perform window management on Linux,
like AutoHotKey for Windows or Applescript for Mac. This is an example
of using it

```python
from xdotool import xdotool
wid = xdotool("search", "--onlyvisible", "--class", "rstudio")
xdotool("key", "--window", wid, "--clearmodifiers", "Return")
```
