#!/usr/bin/env python
import evdev
import selectors

LETTERS = dict(q=16, w=17, e=18, r=19, t=20, z=21, u=22, i=23, o=24, p=25,
               a=30, s=31, d=32, f=33, g=34, h=35, j=36, k=37, l=38,
               y=44, x=45, c=46, v=47, b=48, n=49, m=50)
LETTERS_MAP = {v: k for k, v in LETTERS.items()}

# long int, long int, unsigned short, unsigned short, unsigned int
FORMAT = 'llHHI'
# EVENT_SIZE = struct.calcsize(FORMAT)

KEYBOARD = evdev.InputDevice('/dev/input/event0')
MEDIA = evdev.InputDevice('/dev/input/event3')


def getch_generator(debug=False, timeout=None):
    """
    usage:

    > for c in getch_generator():
    >   ...

    if key is a letter (a-z) then the letter is returned
    else the name of evdev.ecodes (e.g. 'KEY_RIGHT') . See
    https://github.com/spotify/linux/blob/master/include/linux/input.h
    for a good overview

    timeout: if set to None then the generator is blocking, if set to 0.5
             after 0.5s with no input None is returned (timeout mode).
             If set to -1 then it immediately returns (non blocking mode)
    """
    selector = selectors.DefaultSelector()
    selector.register(KEYBOARD, selectors.EVENT_READ)
    selector.register(MEDIA, selectors.EVENT_READ)
    while True:
        in_timeout = True
        for key, mask in selector.select(timeout):
            in_timeout = False
            device = key.fileobj
            for event in device.read():
                if event.type == evdev.ecodes.EV_KEY and event.value != 0:
                    scancode = event.code
                    key = evdev.ecodes.KEY[scancode]
                    if debug:
                        print(key)
                    if scancode in LETTERS_MAP:
                        yield LETTERS_MAP[scancode]
                    else:
                        yield key
        if in_timeout:
            yield None


if __name__ == '__main__':
    for i in getch_generator(debug=True, timeout=5):
        pass
