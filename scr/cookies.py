import sqlite3
import argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys


def export_cookies():
    conn = sqlite3.connect(args.path / args.db)
    cur = conn.cursor()
    lines = ["# Netscape HTTP Cookie File\n"]

    for host, is_http_only, path, is_secure, expiry, name, value in cur.execute(
        "SELECT host, isHttpOnly, path, isSecure, expiry, name, value FROM moz_cookies"
    ):
        lines.append(
            "\t".join(
                [
                    host,
                    "TRUE" if host.startswith(".") else "FALSE",
                    path,
                    "TRUE" if is_secure else "FALSE",
                    str(expiry),
                    name,
                    value,
                ]
            )
            + "\n"
        )

    conn.close()
    return "".join(lines)


class CookieHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == f"/{args.token}":
            cookies_txt = export_cookies()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(cookies_txt.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    add = ap.add_argument

    # fmt: off
    add("-p", "--path", type=Path, help=r"path to ff profile (..\Profiles\xxxxxxxx.floorpdef)")
    add("--db", type=str, default="cookies.sqlite", help="db name (cookies.sqlite)")
    add("--host", type=str, default="127.0.0.1")
    add("--port", type=int, default=9999)
    add("-t", "--token", type=str, default='cookies', help="url to grab cookies")
    # fmt: on

    args = ap.parse_args()

    if not args.path or not args.path.exists():
        ap.print_help(sys.stderr)
        sys.exit(1)

    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, CookieHandler)
    print(f"serving on http://{server_address[0]}:{server_address[1]}/{args.token}")
    httpd.serve_forever()
