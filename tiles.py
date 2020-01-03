import json
from threading import Timer
from PIL import Image, ImageDraw, ImageFont
import requests
import configuration

cfg = configuration.cfg

# thanks, StackOverflow!
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

fontsLoaded = {}

def getFont(fontName, fontSize):
    if (fontName, fontSize) not in fontsLoaded:
        fontsLoaded[(fontName, fontSize)] = ImageFont.truetype("fonts/" + fontName + ".ttf",
                                                               fontSize)
    return fontsLoaded[(fontName, fontSize)]

def newTileImage(backgroundColor="black"):
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
                 font="Ubuntu-Regular",
                 fontSize=36):
        self.text = text
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.fontName = font
        self.fontSize = fontSize
        self.font = getFont(font, fontSize)

    def render(self):
        image, draw = newTileImage(self.backgroundColor)
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
                 font="Ubuntu-Regular",
                 fontSize=36):
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.fontName = font
        self.fontSize = fontSize
        self.font = getFont(font, fontSize)

    def render(self):
        tempC, tempF = getCPUTemp()
        image, draw = newTileImage(self.backgroundColor)
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
        icon = Image.open("images/thermometer.png").resize((150, 150),
                                                           resample=configuration.resizeFilter)
        image.paste(icon,
                    (int(cfg["tileSizeLarge"] / 2) - 75,
                     int(cfg["tileSizeLarge"] / 2) - 75),
                    mask=icon)
        return image

class WeatherCurrentTile:
    def __init__(self,
                 textColor="white",
                 backgroundColor="black",
                 font="Ubuntu-Regular",
                 fontSize=36):
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.fontName = font
        self.fontSize = fontSize
        self.font = getFont(font, fontSize)
        self.updateWeatherCurrent()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherCurrent)
        self.timer.start()

    def updateWeatherCurrent(self):
        resp = requests.get("https://api.openweathermap.org/data/2.5/weather?id=" +
                            cfg["openWeatherCityID"] +
                            "&APPID=" +
                            cfg["openWeatherAPIKey"])
        self.weather = json.loads(resp.text)
        self.tempF = (self.weather["main"]["temp"] - 273.15) * 1.8 + 32 # convert K to F
        self.condition = self.weather["weather"][0]["main"]
        self.icon = "images/openweather/" + \
                    self.weather["weather"][0]["icon"] + \
                    "@2x.png"

    def render(self):
        image, draw = newTileImage(self.backgroundColor)
        # top text
        text = "Current Weather"
        size = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (size[0] / 2),
                   (size[1] + 10)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # bottom text
        text = "%.0f F and %s" % \
               (self.tempF,
                self.condition)
        size = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (size[0] / 2),
                   (cfg["tileSizeLarge"] - (2 * size[1]) - 10)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # icon
        icon = Image.open(self.icon).resize((150, 150), resample=configuration.resizeFilter)
        image.paste(icon,
                    (int(cfg["tileSizeLarge"] / 2) - 75,
                     int(cfg["tileSizeLarge"] / 2) - 75),
                    mask=icon)
        return image

#class WeatherForecastTile(object):
#    def __init__(self):
#
#    def renderLarge(self, parentWidget):
#
#    def renderSmall(self, parentWidget):
