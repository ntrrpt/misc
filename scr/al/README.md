# orange pi pc instructions:

1. enable i2c / spi overlays in boot config
   (https://learn.adafruit.com/circuitpython-on-orangepi-linux/orange-pi-pc-setup)

2. apt install python3.13-dev libjpeg-dev libfreetype-dev i2c-tools mpg123

3. ./build https://github.com/zhaolei/WiringOP

4. uv run al.py (via root) 