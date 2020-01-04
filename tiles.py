import array
import time
from datetime import date, datetime, timedelta
import json
from threading import Timer
from PIL import Image, ImageDraw, ImageFont
import requests
import configuration

cfg = configuration.cfg

fontsLoaded = {}

def getFont(fontName, fontSize):
    if (fontName, fontSize) not in fontsLoaded:
        fontsLoaded[(fontName, fontSize)] = ImageFont.truetype("fonts/" + fontName + ".ttf",
                                                               fontSize)
    return fontsLoaded[(fontName, fontSize)]

def newTileImage(backgroundColor="black", backgroundImage=None):
    if backgroundImage is not None:
        image = Image.open("images/" + backgroundImage).resize((cfg["tileSizeLarge"],
                                                                cfg["tileSizeLarge"]),
                                                               resample=configuration.resizeFilter)
    else:
        image = Image.new("RGBA",
                          (cfg["tileSizeLarge"],
                           cfg["tileSizeLarge"]),
                          color=backgroundColor)
    draw = ImageDraw.Draw(image)
    return image, draw

def getCPUTemp():
    with open('/sys/class/thermal/thermal_zone0/temp') as file:
        read = file.read()
    tempC = int(int(read) / 1000)
    tempF = int(tempC * 1.8 + 32)
    return (tempC, tempF)

class TextTile:
    def __init__(self,
                 text="TILE",
                 textColor="white",
                 backgroundColor="black",
                 backgroundImage=None,
                 font="Ubuntu-Regular",
                 fontSize=36):
        self.text = text
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.backgroundImage = backgroundImage
        self.fontName = font
        self.fontSize = fontSize
        self.font = getFont(font, fontSize)

    def render(self):
        image, draw = newTileImage(self.backgroundColor, self.backgroundImage)
        size = draw.textsize(self.text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (size[0] / 2),
                   (cfg["tileSizeLarge"] / 2) - (size[1] / 2)),
                  self.text,
                  font=self.font,
                  fill=self.textColor)
        return image

class CPUTemperatureTile:
    def __init__(self,
                 textColor="white",
                 backgroundColor="black",
                 backgroundImage=None,
                 font="Ubuntu-Regular",
                 fontSize=36):
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.backgroundImage = backgroundImage
        self.fontName = font
        self.fontSize = fontSize
        self.font = getFont(font, fontSize)

    def render(self):
        tempC, tempF = getCPUTemp()
        image, draw = newTileImage(self.backgroundColor, self.backgroundImage)
        # top text
        text = "CPU Temp"
        size = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (size[0] / 2),
                   (size[1] + 10)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # bottom text
        text = str(tempC) + " C / " + str(tempF) + " F"
        size = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (size[0] / 2),
                   (cfg["tileSizeLarge"] - (2 * size[1]) - 10)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # icon
        with Image.open("images/thermometer.png") \
            .resize((150, 150), resample=configuration.resizeFilter) as icon:
            image.paste(icon,
                        (int(cfg["tileSizeLarge"] / 2) - 75,
                         int(cfg["tileSizeLarge"] / 2) - 75),
                        mask=icon)
        return image
