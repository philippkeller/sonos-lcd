#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image, ImageDraw, ImageFont
import os
import sys
import time
from collections import defaultdict

from timeit import default_timer as timer
import gettext


SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

translate = gettext.translation('base', os.path.join(SCRIPT_DIR, 'locales'))
_ = translate.gettext

NUM_ROWS = 7
# found here: https://www.dafont.com/bitmap.php
FONT = ImageFont.truetype(f'{SCRIPT_DIR}/minecraftia.ttf', 8)
FONT_SMALL = ImageFont.truetype(f'{SCRIPT_DIR}/minecraftia.ttf', 6)
COLOR_HIGHLIGHT = (210, 0, 125)
COLOR_GREY = (80, 80, 80)
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
PADDING = 10

# after how many seconds no keypress does the screen redraw
# (to e.g. show volume changes done right at the sonos speakers)

KEYPRESS_TIMEOUT = 2

IDLE_SLEEP_TIMEOUT = 30

CONTEXTS = [dict(id='albums', name='album'),
            dict(id='tracks', name='song'),
            dict(id='artists', name='artist'),
            dict(id='radio_stations', name='radio'),
            ]


class Status():
    def __init__(self):
        self.entered = ''
        self.row = 0
        self.offset = 0
        self.speaker = 0
        self.context = 0
        self._redraw_screen = False
        self._search_sonos = False
        self._refetch_volume = False

    def __setattr__(self, name, value):
        if name in ['entered', 'offset', 'context']:
            self._search_sonos = True
        if name == '_refetch_volume' or not name.startswith('_'):
            self._redraw_screen = True
        super(Status, self).__setattr__(name, value)

    def should_search_sonos(self, reset=True):
        """
        did something change so search to sonos should be sent?
        """
        res = self._search_sonos
        if reset:
            self._search_sonos = False
        return res

    def should_redraw_screen(self, reset=True):
        """
        did something change so screen should be redrawn?
        """
        res = self._redraw_screen
        if reset:
            self._redraw_screen = False
        return res

    def should_refetch_volume(self, reset=True):
        """
        did something change so volume info should be refetched?
        """
        res = self._refetch_volume
        if reset:
            self._refetch_volume = False
        return res

    def row_up(self):
        if self.row == 0:
            if self.offset > 0:
                self.offset -= 1
        else:
            self.row -= 1

    def row_down(self, items):
        if self.row >= NUM_ROWS - 1:
            self.offset += 1
        else:
            if self.row < len(items) - 1:
                self.row += 1


class Controller():
    def __init__(self, keyboard, display, sonos, debug=False):
        self.line_height = 10

        self.keyboard = keyboard
        self.display = display
        self.sonos = sonos
        self.debug = debug
        self.image = Image.new('RGB', (display.width, display.height))
        self.draw = ImageDraw.Draw(self.image)
        self.speakers = self.sonos.speakers()
        self.status = Status()
        self.last_drawn = defaultdict(list)
        self.count_idle = 0

    def dialogue(self, options):
        DIAG_PADDING = 5
        chosen = 0
        inp = self.keyboard.getch_generator(debug=self.debug)
        image_dialogue = self.image.copy()
        draw_dialogue = ImageDraw.Draw(image_dialogue)
        while True:
            _, h = FONT.getsize('E')
            height = len(options) * h + (DIAG_PADDING * (len(options)))
            width = max(FONT.getsize(o)[0] for o in options) + 2*DIAG_PADDING
            x = (self.display.width - width)/2
            y = (self.display.height - height)/2
            draw_dialogue.rectangle(
                (x, y, x+width, y+height), fill=COLOR_GREY, outline=COLOR_WHITE)
            for i, o in enumerate(options):
                if i == chosen:
                    draw_dialogue.rectangle(
                        (x+1, y+1, x+width-1, y+h+DIAG_PADDING), fill=COLOR_HIGHLIGHT)
                    col = COLOR_BLACK
                else:
                    col = COLOR_WHITE

                draw_dialogue.text(
                    (x+DIAG_PADDING, y+DIAG_PADDING), o, font=FONT, fill=col)
                y += h + DIAG_PADDING - 1
            self.display.draw(image_dialogue)
            c = next(inp)
            if c == 'KEY_DOWN':
                chosen = (chosen + 1) % len(options)
                print('down')
                continue
            elif c == 'KEY_UP':
                chosen = (chosen - 1) % len(options)
                print('up')
                continue

            self.display.draw(self.image)

            if c == 'KEY_ENTER':
                return chosen
            else:
                return None

    def should_redraw(self, _id, *data):
        """
        see if something in this area has changed so self.draw.* should
        be triggered. As most of the CPU time goes into PIL redrawing
        this should give quite a bit of a performance boost
        """
        res = True
        if self.last_drawn[_id] == data:
            res = False
        self.last_drawn[_id] = data
        return res

    def refresh(self):
        start = timer()
        if self.debug:
            print()

        # display speakers
        if self.should_redraw('speakers', self.speakers, self.status.speaker):
            start = timer()
            x = PADDING
            for i, speaker in enumerate(self.speakers):
                text_width, _ = FONT.getsize(speaker)
                if i == self.status.speaker:
                    self.draw.rectangle((x-(PADDING/2), 0, x+text_width, self.line_height),
                                        fill=COLOR_HIGHLIGHT)
                    self.draw.text((x, 0), speaker, font=FONT, fill=(0, 0, 0))
                else:
                    self.draw.rectangle((x-(PADDING/2), 0, x+text_width, self.line_height),
                                        fill=COLOR_BLACK)
                    self.draw.text((x, 0), speaker, font=FONT)
                x += text_width + PADDING
            if self.debug:
                print(f'draw speakers: {timer() - start:.6f}')

        # display volume and play/pause symbol
        if self.should_redraw('volume', self.vol_play):
            start = timer()
            text_width, _ = FONT.getsize(self.vol_play)
            x = self.display.width-(text_width*1.5)
            self.draw.rectangle(
                (x, 0, x+text_width*1.5, self.line_height), fill=COLOR_BLACK)
            self.draw.text((self.display.width-text_width, 0), self.vol_play,
                           font=FONT, fill=(99, 99, 99))
            if self.debug:
                print(f'draw volume: {timer() - start:.6f}')

        # display search results
        start = timer()
        line_no = 0
        for line_no, line_str in enumerate([i[0] for i in self.items[:NUM_ROWS]]):
            if self.should_redraw(f'results_line_{line_no}', line_str, line_no == self.status.row):
                x, y = PADDING, 20 + line_no*self.line_height
                if line_no == self.status.row:
                    self.draw.rectangle(
                        (x-(PADDING/2), y, x+self.display.width, y+self.line_height), fill=COLOR_HIGHLIGHT)
                    self.draw.text((x, y), line_str, font=FONT, fill=(0, 0, 0))
                else:
                    self.draw.rectangle(
                        (x-(PADDING/2), y, x+self.display.width, y+self.line_height), fill=COLOR_BLACK)
                    self.draw.text((x, y), line_str, font=FONT)
        # draw remaining lines black
        for line_no2 in range(line_no + 1, NUM_ROWS):
            if self.should_redraw(f'results_line_{line_no2}', ''):
                x, y = PADDING, 20 + line_no2*self.line_height
                self.draw.rectangle(
                    (x-(PADDING/2), y, x+self.display.width, y+self.line_height), fill=COLOR_BLACK)
        if self.debug:
            print(f'draw results: {timer() - start:.6f}')

        # display enter area
        if self.should_redraw('enter', self.status.entered, self.status.context):
            start = timer()
            x, y = 10, 95
            self.draw.rectangle(
                (x, y, x+self.display.width, y+self.line_height), fill=COLOR_BLACK)
            if self.status.context != 3:
                self.draw.text((10, 95), f"> {self.status.entered}", font=FONT)
            if self.debug:
                print(f'draw search text: {timer() - start:.6f}')

        # display contexts (f1, f2, …)
        if self.should_redraw('contexts', self.status.context):
            start = timer()
            x = PADDING
            for i, c in enumerate(CONTEXTS):
                f = f'F{i+1}'
                txt = c['name']
                if i == self.status.context:
                    color_text = (0, 0, 0)
                    color_box = COLOR_WHITE
                else:
                    color_text = COLOR_WHITE
                    color_box = COLOR_GREY
                width = 25
                text_width, _ = FONT.getsize(txt)
                padding = (width-text_width)/2
                self.draw.rectangle((x, 110, x+width, 125), fill=color_box)
                self.draw.text((x+9, 111), f, font=FONT_SMALL, fill=color_text)
                self.draw.text((x+3+padding, 117), txt,
                               font=FONT_SMALL, fill=color_text)
                x += width + 3
            if self.debug:
                print(f'draw contexts: {timer() - start:.6f}')

        if self.debug:
            start = timer()
        self.display.draw(self.image)
        if self.debug:
            print(f'display: {timer() - start:.4f}')

    def handle_keypress(self, c):
        if c == 'KEY_BACKSPACE':
            self.status.entered = self.status.entered[:-1]
            self.status.row = 0
        elif c == 'KEY_UP':
            self.status.row_up()
        elif c == 'KEY_DOWN':
            self.status.row_down(self.items)
        elif c == 'KEY_LEFT':
            self.status.speaker = (
                self.status.speaker - 1) % len(self.speakers)
            self.status._refetch_volume = True
        elif c == 'KEY_RIGHT':
            self.status.speaker = (
                self.status.speaker + 1) % len(self.speakers)
            self.status._refetch_volume = True
        elif c == 'KEY_ENTER':
            if CONTEXTS[self.status.context]['id'] == 'radio_stations':
                self.sonos.play(self.status.speaker,
                                self.items[self.status.row][1])
            else:
                choice = self.dialogue([_('replace'), _('add to end of queue')])
                if choice == 0:
                    if self.debug:
                        print(f'playing {self.items[self.status.row][0]}')
                    self.sonos.play(self.status.speaker,
                                    self.items[self.status.row][1])
                elif choice == 1:
                    if self.debug:
                        print(
                            f'add to end of queue: {self.items[self.status.row][0]}')
                    self.sonos.add_to_queue(
                        self.status.speaker, self.items[self.status.row][1])
            self.status._refetch_volume = True
        elif c == 'KEY_PLAYPAUSE':
            self.sonos.play_pause(self.status.speaker)
            self.status._refetch_volume = True
        elif c == 'KEY_VOLUMEUP':
            self.sonos.change_volume(self.status.speaker, 2)
            self.status._refetch_volume = True
        elif c == 'KEY_VOLUMEDOWN':
            self.sonos.change_volume(self.status.speaker, -2)
            self.status._refetch_volume = True
        elif c == 'KEY_NEXTSONG':
            self.sonos.next(self.status.speaker)
        elif c == 'KEY_PREVIOUSSONG':
            self.sonos.previous(self.status.speaker)
        elif c == 'KEY_SEARCH':
            self.sonos.reindex()
        elif c == 'KEY_CONFIG':
            self.sonos.cycle_repeat(self.status.speaker)
            self.status._refetch_volume = True
        elif c == 'KEY_F1':
            self.status.context = 0
        elif c == 'KEY_F2':
            self.status.context = 1
        elif c == 'KEY_F3':
            self.status.context = 2
        elif c == 'KEY_F4':
            self.status.context = 3
        elif c == 'KEY_F5':
            self.status.context = 4
        elif c is not None and len(c) == 1:
            self.status.entered += c
            self.status.row = 0
        elif c is not None and self.debug:
            print(f'handling of {c} not supported')

        if c is None:
            self.count_idle += 1
            if self.count_idle * KEYPRESS_TIMEOUT >= IDLE_SLEEP_TIMEOUT:
                self.sleep()
            self.status._refetch_volume = True
        else:
            self.count_idle = 0

    def sleep(self):
        """
        turn screen to black and wait for keypress before waking up
        """
        self.display.display_off()
        gen = self.keyboard.getch_generator(debug=self.debug)
        next(gen)
        self.display.display_on()

    def loop(self):
        """
        k: keyboard module/object, needs to provide `getch_generator()`
        display: display module/objects, needs to provide `image(pil_image)`, `width` and `height`
        s: instance of sonos, needs to provide a dozen functions, see sonos module
        """

        self.vol_play = self.sonos.volume_play_as_string(self.status.speaker)
        self.items = self.sonos.search(CONTEXTS[self.status.context]['id'], '',
                                       max_items=NUM_ROWS, debug=self.debug)
        self.refresh()

        for c in self.keyboard.getch_generator(debug=self.debug, timeout=KEYPRESS_TIMEOUT):
            try:
                self.handle_keypress(c)

                if self.status.should_search_sonos():
                    self.items = self.sonos.search(CONTEXTS[self.status.context]['id'],
                                                   self.status.entered, max_items=NUM_ROWS,
                                                   offset=self.status.offset, debug=self.debug)

                if self.status.should_refetch_volume():
                    self.vol_play = self.sonos.volume_play_as_string(
                        self.status.speaker, debug=self.debug)

                if self.status.should_redraw_screen():
                    self.refresh()
            except Exception as e:
                f = open('/tmp/sonos_lcd.log', 'a+')
                f.write(str(e) + "\n")
                f.close()
                print(e)


def main_raspberry():
    """
    call main from a raspberry environment
    """
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'debug':
        DEBUG = True
    else:
        DEBUG = False
    import screen
    import keyboard
    from sonos import Sonos
    display = screen.Screen()
    c = Controller(keyboard, display, Sonos(), debug=DEBUG)
    c.loop()


def main_development():
    """
    call main with mock objects for development
    """

    import sys

    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} [wlan|vpn|mock]")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == 'wlan':
        import sonos
        s = sonos.Sonos()
    elif mode == 'vpn':
        import soco
        import sonos
        s1 = soco.SoCo("192.168.188.24")
        s2 = soco.SoCo("192.168.188.26")
        from sonos import Sonos
        s = sonos.Sonos([s1, s2])
    elif mode == 'mock':
        from mock import Sonos
        s = Sonos()
    else:
        print(f"unknown mode {mode}")
        sys.exit(1)

    from mock import Keyboard, Display
    c = Controller(Keyboard(), Display(), s, debug=True)
    c.loop()


if __name__ == "__main__":
    if sys.platform == 'darwin':
        main_development()
    else:
        main_raspberry()
