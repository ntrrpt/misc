# py's

| file                                                               | desc                                                         |
| ------------------------------------------------------------------ | ------------------------------------------------------------ |
| [scr]                                                              | imageboard scrappers                                         |
| cookies.py                                                         | http server that converts firefox cookies to netscape format |
| ff2size.py                                                         | compressing video to a specified size via ffmpeg             |
| knock.py                                                           | port knocker for windows                                     |
| pefa4.py                                                           | abaqus .sta viewer                                           |
| twd.py                                                             | twitter search scrapper (rip my 9yo account)                 |
| [sync.py](https://github.com/ntrrpt/misc/blob/main/termux/sync.py) | rsync wrapper with folder exclusion support                  |

```bash
# almost all of this is run via uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv run script.py
```