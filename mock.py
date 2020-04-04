#!/usr/bin/env python
"""
provide mock objects in order to develop locally
"""

from PIL import Image, ImageTk, ImageFilter
import time
import tty, sys

PADDING = 10

class Keyboard:
  def __init__(self):
    tty.setcbreak(sys.stdin)
  def getch_generator(self, debug=False, timeout=None):
    while True:
      c = sys.stdin.read(1)

      if ord(c) == 27:
        c2 = sys.stdin.read(1)
        if c2 == '[':
          c3 = sys.stdin.read(1)
          if c3 == 'D':
            yield 'KEY_LEFT'
          elif c3 == 'A':
            yield 'KEY_UP'
          elif c3 == 'C':
            yield 'KEY_RIGHT'
          elif c3 == 'B':
            yield 'KEY_DOWN'
          elif c3 == '1':
            c4 = sys.stdin.read(2)
            if c4 == '5~':
              yield 'KEY_F5'
            elif c4 == '7~':
              yield 'KEY_F6'
            elif c4 == '8~':
              yield 'KEY_F7'
            elif c4 == '9~':
              yield 'KEY_F8'
            else:
              print('unknown F key: ' + c4)
              yield 'DUMMY'
        elif c2 == 'O':
          c3 = sys.stdin.read(1)
          yield f'KEY_F{ord(c3)-79}'
        else:
          print(f'unknown control character {suff}')
          yield 'AA'
      elif ord(c) == 127:
        yield 'KEY_BACKSPACE'
      elif ord(c) == 10:
        yield 'KEY_ENTER'
      else:
        yield c

class Sonos:
  def speakers(self):
    return ['Schwarz', 'Weiss']
  def volume_play_as_string(self, selected_speaker, debug=False):
    return "> 50%"
  def search(self, context, term, offset=0, max_items=7, debug=False):
    res = []
    if context == 'albums':
      res = ['Appetite for Destruction', 'OK Computer', 'The Four Seasons', 
              'Music for a jilted generation']
    elif context == 'tracks':
      res = ['Hamba hamba', 'Everybody', 'Take Five', 'Paranoid Android']

    return [(i, i) for i in res] 
  def play(self, speaker, uri):
    print(f'play {uri} on {speaker}')

class Display:
  width=160
  height=128

  def __init__(self):
    import tkinter as tk
    from PIL import Image, ImageTk, ImageFile
    self._root = tk.Tk()
    self._canvas = tk.Canvas(self._root, width=self.width+2*PADDING, height=self.height+2*PADDING)
    self._imgArea = self._canvas.create_image(PADDING, PADDING, anchor=tk.NW)
    self._canvas.pack()
    self._canvas.configure(background='black')
    self._root.update()
  
  def __del__(self):
    self._root.quit()
  
  def draw(self, image):
    img = ImageTk.PhotoImage(image)
    self._canvas.itemconfig(self._imgArea, image=img)
    self._root.update()
    # image.show()

if __name__ == "__main__":
  k = Keyboard()
  for c in k.getch_generator():
    print('>>' + c)
    pass
