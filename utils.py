from threading import Timer
import pygame


fontsLoaded = {}


class RepeatTimer(Timer):
    # thanks, StackOverflow!
    def __init__(self, interval, function):
        super().__init__(interval, function)
        self.daemon = True

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def getFont(fontName, fontSize):
    if (fontName, fontSize) not in fontsLoaded:
        fontsLoaded[(fontName, fontSize)] = pygame.font.Font("fonts/" + fontName + ".ttf",
                                                             fontSize)
    return fontsLoaded[(fontName, fontSize)]


def placeTile(source, target, size, loc, fast=False):
    if size is not None:
        resized = pygame.Surface(size)
        if fast:
            pygame.transform.scale(source, size, resized)
        else:
            pygame.transform.smoothscale(source, size, resized)
        target.blit(resized, loc)
    else:
        target.blit(source, loc)


def tupleColor(RGBString):
    # convert a string of the form "#RRGGBB" to an (R, G, B) tupleColor
    if RGBString is None:
        return None
    if RGBString.startswith("#") and len(RGBString) == 7:
        return (int(RGBString[1:3], base=16),
                int(RGBString[3:5], base=16),
                int(RGBString[5:], base=16))
    return (0, 0, 0)


def getCPUTemp():
    with open('/sys/class/thermal/thermal_zone0/temp') as file:
        read = file.read()
    tempC = int(int(read) / 1000)
    tempF = int(tempC * 1.8 + 32)
    return (tempC, tempF)

# Special string flattener to remove code points above FFFF
# from strings passed to pygame. I feel like there has to
# be a built-in way to do this, but I couldn't find it.


class StringFlattener:
    def __getitem__(self, key):
        if key > 0xFFFF:
            return None
        return key


def flattenString(str):
    return str.translate(StringFlattener())
