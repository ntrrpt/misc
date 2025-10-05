# py's

| file                                                               | desc                                                                                         |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| [scr](https://github.com/ntrrpt/misc/tree/main/py/scr)             | imageboard scrappers                                                                         |
| cookies.py                                                         | http server that converts firefox cookies to netscape format                                 |
| ff_size.py                                                         | compressing video to a specified size via ffmpeg                                             |
| ff_shrink.py                                                       | recoding video to mp4 and deleting the smaller file (for [yk](https://github.com/ntrrpt/yk)) |
| knock.py                                                           | port knocker for windows                                                                     |
| pefa4.py                                                           | tail -f abaqus .sta                                                                          |
| twd.py                                                             | twitter search scrapper (rip my 9yo account)                                                 |
| [sync.py](https://github.com/ntrrpt/misc/blob/main/termux/sync.py) | rsync wrapper with folder exclusion support                                                  |
| flcl.py                                                            | recursive fclones                                                                            |
| uvass.py                                                           | associate files with uv run --script (.uv) on windows                                        |

```bash
# almost all of this is run via uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv run script.py
```
