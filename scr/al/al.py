import argparse
import os
import shlex
import subprocess as sp
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from sys import exit as die
from time import sleep

import schedule
import tomli_w
import tomllib
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from loguru import logger as log

app = FastAPI()

# mpg123 subprocess
RING = None

# RING_TIME (RING_TIME)
RING_TIME = (-1, -1)

# fonts for oled
FNT18 = FNT18b = FNT32b = None

# oled object
DISP = None

# need for oled updating
OLED_SEC = 0

# need for big clock and sleep mode after 'args.oled_sleep'
OLED_SLEEP = time.time()

# need for 'args.reset' chk
TS_NOW = time.time()


def now_time():
    t = datetime.now().time()
    return t.hour, t.minute, t.second


def now_date():
    d = datetime.now().date()
    return d.year, d.month, d.day


def time_until(hhmm: str):
    now = datetime.now()
    target = datetime.strptime(hhmm, "%H:%M").replace(
        year=now.year, month=now.month, day=now.day
    )
    if target <= now:
        target += timedelta(days=1)
    delta = target - now
    hh, remainder = divmod(delta.seconds, 3600)
    mm = remainder // 60
    return f"{hh}:{mm:02d}"


def at_read():
    with open(args.config, "rb") as file:
        data = tomllib.load(file)
        at = data.get("alarm_time", None)
        if at:
            hh = at.get("hh", -1)
            mm = at.get("mm", -1)
            return (hh, mm)


def at_write(rt):
    with open(args.config, "wb") as file:
        tomli_w.dump({"alarm_time": {"hh": rt[0], "mm": rt[1]}}, file)


def at_set(hhmm):
    global RING_TIME

    RING_TIME = hhmm
    at_write(hhmm)

    schedule.clear()
    if at_chk(hhmm):
        schedule.every().day.at("%02d:%02d" % hhmm).do(play)


def at_chk(rt: tuple[int, int]) -> bool:
    return all(t > -1 for t in rt)


def sp_exec(cmd: str | list):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    try:
        p = sp.run(cmd, check=True, capture_output=True, text=True)
        return p.stdout, p.stderr
    except sp.CalledProcessError as e:
        log.error(f"failed cmd: {cmd!r} => {e}")


def gpio_chk(pin: str):
    if pin < 0:
        return False

    s, _ = sp_exec(f"gpio read {pin}")
    return s.rstrip() == "1"


def gpio_set(pin: int, state: int):
    if pin > 0:
        sp_exec(f"gpio write {pin} {state}")


def vol_set(value: str):
    sp_exec(f"amixer set DAC {value}")
    log.info(f"volume changed: {value}")


def vol_raise(delta: int) -> None:
    sign = "-" if delta < 0 else "+"
    value = f"{abs(delta)}%{sign}"

    vol_set(value)


def load_font(filename: str, size: int):
    from PIL import ImageFont

    try:
        font = ImageFont.truetype(filename, size)
    except OSError:
        log.warning(
            f"failed load {filename.as_posix()!r} with {size} size, fallback to default font"
        )
        font = ImageFont.load_default(size)

    return font


def oled_update(blank: bool = False):
    if args.disable_oled:
        return

    import adafruit_ssd1306
    import board
    import busio
    from PIL import Image, ImageDraw, ImageOps

    global RING, RING_TIME, DISP, OLED_SEC, OLED_SLEEP
    global FNT18, FNT18b, FNT32b

    if not DISP:
        i2c = busio.I2C(board.SCL, board.SDA)
        DISP = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

    if not FNT18:
        FNT18 = load_font(args.ttf, 18)

    if not FNT18b:
        FNT18b = load_font(args.ttf_bold, 18)

    if not FNT32b:
        FNT32b = load_font(args.ttf_bold, 32)

    hh, mm, ss = now_time()
    yy, mo, dd = now_date()

    dots = ":" if ss % 2 else " "
    hhmm = f"{hh:2}{dots}{mm:02}"

    img = Image.new("1", (DISP.width, DISP.height))
    draw = ImageDraw.Draw(img)

    # small clock
    if all(
        [at_chk(RING_TIME), not RING, time.time() - OLED_SLEEP < 60 * args.oled_clock]
    ):
        # hh:mm  A: ##
        # da/te  ri:ng

        # hh:mm
        draw.text((0, 0), hhmm, font=FNT18b, fill=255)

        # dd:mo
        draw.text((0, 16), f"{dd}/{mo}", font=FNT18, fill=255)

        # remaning A: ttempts
        draw.text((80, 0), f"A: {args.snooze_max}", font=FNT18, fill=255)

        # ring time
        draw.text((80, 16), f"{RING_TIME[0]}:{RING_TIME[1]:02d}", font=FNT18, fill=255)

    else:
        # ring time indicator (1px border)
        if at_chk(RING_TIME) and not RING:
            draw.rectangle((0, 0, DISP.width - 1, DISP.height - 1), outline=3, fill=0)

        # big clock
        draw.text((12 if hh < 10 else 23, 0), hhmm, font=FNT32b, fill=255)

    # blinking screen
    if RING and (not args.snooze_max or time.time() % 0.5 < 0.25):
        img = ImageOps.invert(img)

    DISP.fill(0)

    if not blank and (RING or time.time() - OLED_SLEEP < 60 * args.oled_sleep):
        DISP.image(img)

    DISP.show()


@app.get("/kill", response_class=PlainTextResponse)
def kill():
    import signal

    stop()
    at_set((-1, -1))
    oled_update(blank=True)
    os.kill(os.getpid(), signal.SIGINT)
    return "rip"


@app.get("/reboot", response_class=PlainTextResponse)
def reboot():
    stop()
    at_set((-1, -1))
    sp_exec("sudo shutdown -r now")
    return "reboot ok"


@app.get("/poweroff", response_class=PlainTextResponse)
def poweroff():
    stop()
    at_set((-1, -1))
    sp_exec("sudo shutdown now")
    return "poweroff ok"


# playing sound
@app.get("/play", response_class=PlainTextResponse)
def play():
    global RING, OLED_SEC, TS_NOW
    if RING:
        s = "ringing already"
        log.warning(s)
        return s

    # volume up every minute
    if args.volume_raise:
        schedule.every().minute.do(vol_raise, delta=args.volume_raise)

    # turn on speakers
    gpio_set(args.pin_relay, 1)

    TS_NOW = time.time()
    OLED_SEC = -1

    # playing mp3
    c = ["mpg123", "-Z"] + args.path  # '--loop', '-1'
    RING = sp.Popen(c, stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    log.trace(f"play cmd: {c}")

    log.success("playing")
    return "playing"


# stopping sound
@app.get("/stop", response_class=PlainTextResponse)
def stop():
    global RING

    if not RING:
        s = "ringing already stopped"
        log.warning(s)
        return s

    # turn off speakers
    gpio_set(args.pin_relay, 0)

    RING.terminate()
    RING.wait()
    RING = None

    log.info("stopped")
    return "stopped"


# stopping sound with delaying alarm time
@app.get("/snooze", response_class=PlainTextResponse)
def snooze():
    global RING, OLED_SLEEP, OLED_SEC

    if not RING:
        s = "ringing already stopped"
        log.warning(s)
        return s

    if not args.snooze_max:
        s = "max snoozes reached"
        log.warning(s)
        return s

    OLED_SLEEP = time.time()
    stop()

    hh, mm, _ = now_time()
    r = f"snoozed: {hh}:{mm:02d} => "

    args.snooze_max -= 1
    mm += args.snooze_time

    if mm > 59:
        mm -= 60
        hh += 1
        if hh > 23:
            hh -= 24

    at_set((hh, mm))

    OLED_SEC = -1

    r += f"{hh}:{mm:02d} ({args.snooze_max} remaining)"
    log.info(r)
    return r


# setting time
@app.post("/set", response_class=PlainTextResponse)
async def _set(request: Request):
    global RING, RING_TIME, OLED_SLEEP, OLED_SEC

    if not args.snooze_max:
        s = "max snoozes reached"
        log.warning(s)
        return s

    if RING:
        stop()

    try:
        request_data = await request.json()
    except Exception:
        raise HTTPException(status_code=403, detail="no data")

    hh, mm = RING_TIME[0], 0

    hhmm = request_data.get("hhmm")
    if isinstance(hhmm, str):
        hhmm = hhmm.replace("'", "").strip()
        try:
            hh, mm = map(int, hhmm.split(":"))  # TODO
        except ValueError:
            pass

    if isinstance(request_data.get("hh"), int):
        hh = request_data["hh"]

    if isinstance(request_data.get("mm"), int):
        mm = request_data["mm"]

    if hh > 23 or mm > 59:
        raise HTTPException(status_code=403, detail="invalid time!")

    hh = max(0, hh)
    mm = max(0, mm)

    at_set((hh, mm))

    OLED_SEC = -1
    OLED_SLEEP = time.time()

    log.success(f"{RING_TIME[0]}:{RING_TIME[1]:02d} {request_data}")

    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    diff = time_until(f"{hh}:{mm:02d}")

    return (
        "alarm enabled!\n"
        "\n"
        f"DT: {dt}\n"
        f"Alarm time: {hh}:{mm:02d}\n"
        f"Time to ring: {diff}\n"
        "\n"
        f"Snooze delay: {args.snooze_time}\n"
        f"Snoozes left: {args.snooze_max}"
    )


if __name__ == "__main__":
    # fmt: off
    ap = argparse.ArgumentParser()
    add = ap.add_argument

    add('-v', '--verbose', action='store_true',                      help='verbose output (traces)')
    add("-c", "--config",  type=Path, default=Path('config.toml'),   help="path to config.toml")
    add("-p", "--path",    type=Path, default=Path('ponponpon.mp3'), help="path to .mp3 file / folder with .mp3's")

    g = ap.add_argument_group('alarm options')
    add = g.add_argument

    add("--alarm-time",   type=str, default='-1:-1', help="hh:mm to wake up (def: -1:-1 => no alarm)")
    add("--snooze-time",  type=int, default=5,       help="snooze time in minutes")
    add("--snooze-max",   type=int, default=6,       help="max snoozes")
    add("--reset-time",   type=int, default=30,      help="reset after X minutes of playing")
    add("--start-volume", type=int, default=20,      help="initial volume at start")
    add("--volume-raise", type=int, default=3,       help="raising volume every minute by X")

    g = ap.add_argument_group('oled options')
    add = g.add_argument

    def_ttf = Path('TerminusTTF-4.49.3.ttf')
    def_ttfb = Path('TerminusTTF-Bold-4.49.3.ttf')
    add("--disable-oled", action='store_true',         help="disable oled support")
    add("--oled-clock",   type=int, default=10,        help="big clock after X minutes")
    add("--oled-sleep",   type=int, default=60,        help="blank oled after X minutes") 
    add("--ttf",          type=Path, default=def_ttf,  help="main font for oled")
    add("--ttf-bold",     type=Path, default=def_ttfb, help="bold font for oled")

    g = ap.add_argument_group('pin options')
    add = g.add_argument

    add("--pin-button",   type=int, default=5, help="button gpio pin (snooze)")
    add("--pin-relay",    type=int, default=4, help="relay gpio pin (turning on/off speakers)")

    g = ap.add_argument_group('server options')
    add = g.add_argument

    add("--port", type=int, default=5000,      help="server port (def: 5000)")
    add("--host", type=str, default='0.0.0.0', help="server host (def: 0.0.0.0)")

    args = ap.parse_args()
    # fmt: on

    for p in [args.path, args.config, args.ttf, args.ttf_bold]:
        p = Path(p)

    log.add("log.txt")
    if args.verbose:
        from sys import stderr

        log.remove()
        log.add(stderr, level="TRACE")
        log.add("log.txt", level="TRACE", encoding="utf-8")

    # number envs
    for var, target in [
        # main
        ("AL_CONFIG", args.config),
        ("AL_PATH", args.path),

        # alarm
        ("AL_ALARM_TIME", args.alarm_time),
        ("AL_SNOOZE_TIME", args.snooze_time),
        ("AL_SNOOZE_MAX", args.snooze_max),
        ("AL_RESET_TIME", args.reset_time),
        ("AL_START_VOLUME", args.start_volume),
        ("AL_VOLUME_RAISE", args.volume_raise),

        # oled
        ("AL_OLED_CLOCK", args.oled_clock),
        ("AL_OLED_SLEEP", args.oled_sleep),
        ("AL_TTF", args.ttf),
        ("AL_TTF_BOLD", args.ttf_bold),

        # pin
        ("AL_PIN_BUTTON", args.pin_button),
        ("AL_PIN_RELAY", args.pin_relay),

        # server
        ("AL_PORT", args.port),
        ("AL_HOST", args.host),
    ]:  # fmt: skip
        env = os.environ.get(var, "")
        if env:
            target = env

        log.trace(f"{var}: {target}")

    # bool envs
    for var, target in [
        # oled
        ("AL_DISABLE_OLED", args.disable_oled),
    ]:
        env = os.environ.get(var, "")
        if env in ["True", "1"]:
            target = True
        elif env in ["False", "0"]:
            target = False

        log.trace(f"{var}: {target}")

    ##########################
    ## mp3's parsing

    if args.path.is_file():
        if args.path.suffix != ".mp3":
            log.critical(f"invalid .mp3: {args.path.resolve().as_posix()} ")
            die(1)

        args.path = [Path(args.path).resolve().as_posix()]

    elif args.path.is_dir():
        mp3s = [str(f.resolve()) for f in args.path.rglob("*.mp3") if f.is_file()]
        if not mp3s:
            log.critical(
                f"{args.path.resolve().as_posix()!r} doesn't contain .mp3 files"
            )
            die(1)

        args.path = mp3s
    else:
        log.critical(f"invalid path: {args.path.resolve().as_posix()}")
        die(1)

    log.info(f"mp3's: {args.path}")

    ##########################
    ## alarm time parsing

    hhmm = args.alarm_time.split(":")
    hhmm = tuple(map(int, hhmm))  # conv 'hh' and 'mm' to int type
    if len(hhmm) != 2:
        log.error(f"invalid hhmm (len({args.alarm_time}) != 2)")
        die(-1)

    if not args.config.exists():
        if args.config != Path("config.toml"):
            log.critical(f"{str(args.config.resolve())!r} not found")
            die(1)

        at_set(hhmm)

    if hhmm == (-1, -1):
        at_set(at_read())
    else:
        at_set(hhmm)

    ##########################
    ## hw test

    # set start volume
    if args.start_volume:
        vol_set(args.start_volume)

    if args.pin_button:
        # button init
        sp_exec(f"gpio mode {args.pin_button} IN")

    if args.pin_relay:
        # relay init
        sp_exec(f"gpio mode {args.pin_relay} OUT")

        # test relay on / off
        gpio_set(args.pin_relay, 1)
        sleep(1)
        gpio_set(args.pin_relay, 0)

    ##########################
    ## server handling

    def run_server():
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    log.success(f"started: {RING_TIME[0]}:{RING_TIME[1]:02d}")

    ##########################
    ## main loop

    try:
        while True:
            schedule.run_pending()

            btn = gpio_chk(args.pin_button)
            sec = int(time.time())

            # showing small clock on button press
            if btn:
                OLED_SLEEP = time.time()
                OLED_SEC = -1

            if RING:
                oled_update()
                if args.snooze_max and btn:
                    snooze()

                # time out
                if (time.time() - TS_NOW) > args.reset_time * 60:
                    log.critical("time out!")

                    # reboot()
                    kill()

                    while True:
                        pass

            elif OLED_SEC != sec:
                # updating oled on every second
                OLED_SEC = sec
                oled_update()

    except KeyboardInterrupt:
        stop()
        oled_update(blank=True)
