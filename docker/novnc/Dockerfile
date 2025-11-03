FROM ghcr.io/astral-sh/uv:python3.13-alpine

ENV UV_NO_PROGRESS=1
ENV UV_COMPILE_BYTECODE=1
ENV NO_COLOR=1
ENV UV_NO_DEV=1

RUN apk add --no-cache --progress git bash
RUN uv tool install websockify

RUN git clone https://github.com/novnc/noVNC.git /usr/src/app/noVNC
WORKDIR /usr/src/app/noVNC
COPY index.html .

ENTRYPOINT [ "bash", "./utils/novnc_proxy" ]
# docker build -t nouvnc .\
# docker run -p 6080:6080 -it nouvnc --vnc 192.168.0.110:5900


