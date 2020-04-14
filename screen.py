#!/usr/bin/env python

import busio
import digitalio
from board import SCK, MOSI, CE0, D24, D25, D27

from adafruit_rgb_display import color565
import adafruit_rgb_display.st7735 as st7735

class Screen:
  def __init__(self):
    # Setup SPI bus using hardware SPI:
    spi = busio.SPI(clock=SCK, MOSI=MOSI)

    # Create the ST7735S display:
    width = 160
    height = 128
    self.display = st7735.ST7735S(spi, cs=digitalio.DigitalInOut(CE0),
                                  dc=digitalio.DigitalInOut(D25),
                                  rst=digitalio.DigitalInOut(D27),
                                  bl=digitalio.DigitalInOut(D24),
                                  width=width,height=height,x_offset=1,y_offset=2,
                                  )

    self.display.fill(color565(0,0,0))
    self.width = width
    self.height = height

  def display_off(self):
    print('ssss')
    self.display.rst.switch_to_output(False)

  def display_on(self):
    self.display.rst.switch_to_output(True)

  def draw(self, image):
    self.display.image(image)

