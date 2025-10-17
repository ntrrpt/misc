# /// script
# dependencies = [
#     "dearpygui", "pyinstaller", "loguru"
# ]
# ///

import argparse
import random
import shutil
import string
import subprocess as sp
import sys
import threading
import time
from pathlib import Path

from loguru import logger as log

try:
    import dearpygui.dearpygui as dpg
    # import dearpygui.demo as demo
except ImportError:
    log.error("dearpygui import failed")
    log.error("make sure you have installed redists")
    for arch in ["arm64", "x86", "x64"]:
        print(f"curl -fSLO https://aka.ms/vs/17/release/vc_redist.{arch}.exe")

    sys.exit(1)


EXE = bool(getattr(sys, "frozen", False))
PLOT_X, PLOT_Y = [], []
CONSOLE_LOG = []


def add_plot_data():
    while True:
        x, y = len(PLOT_X), random.uniform(0, len(PLOT_Y))
        PLOT_X.append(x)
        PLOT_Y.append(y)
        log.info(f"x: {x}, y: {y}")
        time.sleep(0.1)


def dbg_render():
    ############################
    #   plot

    with dpg.plot(tag="_plot", label="test", height=500, width=-1):
        dpg.add_plot_legend()
        dpg.add_plot_axis(dpg.mvXAxis, label="x", auto_fit=True)
        with dpg.plot_axis(dpg.mvYAxis, label="y", auto_fit=True):
            dpg.add_line_series(PLOT_X, PLOT_Y, label="test", tag="plot")

    def _upd_plot():
        dpg.set_value("plot", [PLOT_X, PLOT_Y])

    with dpg.item_handler_registry(tag="__plot_ref"):
        dpg.add_item_visible_handler(callback=_upd_plot)
    dpg.bind_item_handler_registry("_plot", dpg.last_container())

    with dpg.tab_bar():
        ############################
        #   log
        with dpg.tab(label="Console"):

            def _upd_log():
                global CONSOLE_LOG
                if CONSOLE_LOG:
                    text = "\n".join(CONSOLE_LOG)
                    dpg.set_value("log_field", text)
                    dpg.set_item_height(
                        "log_field", dpg.get_text_size(text)[1] + (2 * 3)
                    )

            def toggle_auto_scroll(checkbox, checked):
                dpg.configure_item("log_field", tracked=checked)

            dpg.add_checkbox(
                label="Autoscroll console",
                default_value=True,
                callback=toggle_auto_scroll,
            )
            with dpg.child_window():
                dpg.add_input_text(
                    tag="log_field",
                    multiline=True,
                    readonly=True,
                    tracked=True,
                    track_offset=1,
                    width=-1,
                    height=-1,
                )

            with dpg.item_handler_registry(tag="_log_field_ref"):
                dpg.add_item_visible_handler(callback=_upd_log)
            dpg.bind_item_handler_registry("log_field", dpg.last_container())

        ############################
        #   table
        with dpg.tab(label="Table"):
            dpg.add_checkbox(
                label="Autoscroll table", tag="autoscroll_table", default_value=True
            )

            with dpg.child_window(
                height=-1, autosize_x=True, horizontal_scrollbar=False
            ) as scroll_region:
                table_id = dpg.add_table(
                    tag="table",
                    header_row=True,
                    borders_outerH=True,
                    borders_outerV=True,
                    borders_innerH=True,
                    borders_innerV=True,
                    resizable=True,
                    policy=dpg.mvTable_SizingStretchProp,
                )

            def _upd_table():
                dpg.delete_item(table_id, children_only=True)

                dpg.add_table_column(label="x", parent=table_id)
                dpg.add_table_column(label="y", parent=table_id)

                for i in range(len(PLOT_X)):
                    with dpg.table_row(parent=table_id):
                        dpg.add_text(PLOT_X[i])
                        dpg.add_text(PLOT_Y[i])

                dpg.set_frame_callback(dpg.get_frame_count() + 5, _upd_table)
                if dpg.get_value("autoscroll_table"):
                    dpg.set_y_scroll(scroll_region, -1.0)

            _upd_table()


def build_exe():
    def is_pyinstaller_available():
        if shutil.which("pyinstaller") is None:
            return False

        try:
            r = sp.run(
                ["pyinstaller", "--version"], capture_output=True, text=True, check=True
            )

            # 6.16.0 => 6160 => digit
            return r.stdout.lower().replace(".", "").strip().isdigit()
        except (sp.CalledProcessError, FileNotFoundError):
            return False

    if not is_pyinstaller_available():
        log.error("pyinstaller not found, make sure you run uvass via uv")
        sys.exit(1)

    me = Path(__file__).resolve()
    workpath = "".join(random.choice(string.ascii_letters) for x in range(10))

    c = [
        "pyinstaller",
        "--onefile",
        "--hide-console", "hide-early",
        "--workpath", workpath,
        "--distpath", str(me.parent),
        str(me),
    ]  # fmt: skip

    sp.run(c, check=True)

    for item in [workpath, me.with_suffix(".stem")]:
        p = Path(item)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


if __name__ == "__main__":
    arg = argparse.ArgumentParser()
    add = arg.add_argument

    add('-v', '--verbose', action='store_true', help='verbose output (traces)')  # fmt: skip
    if not EXE:
        add('--exe', action='store_true', help='make executable')  # fmt: skip

    args = arg.parse_args()

    if not EXE and args.exe:
        build_exe()
        sys.exit(0)

    log.add(
        lambda msg: CONSOLE_LOG.append(msg.strip()),
        format="[{time:YYYY-MM-DD HH:mm:ss.SSS}] [{level}] {message}",
    )

    #####################
    # imgui init

    dpg.create_context()

    dpg.create_viewport(
        title="dpg test", width=900, height=900, clear_color=(0, 0, 0, 0)
    )

    dpg.setup_dearpygui()

    with dpg.window(
        tag="MAIN_WINDOW",
        label="",
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_close=True,
        no_collapse=True,
        no_background=True,
    ):
        dbg_render()

    dpg.set_primary_window("MAIN_WINDOW", True)

    dpg.show_viewport()

    ####################
    # main loop

    T = threading.Thread(target=add_plot_data, daemon=True)
    T.start()

    dpg.start_dearpygui()

    dpg.destroy_context()
