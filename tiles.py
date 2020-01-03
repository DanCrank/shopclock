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

def kelvinToF(kelvin):
    return (float(kelvin) - 273.15) * 1.8 + 32

def bearingToDir(bearing):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    return directions[int((bearing + 11.25) / 22.5)]

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

class WeatherCurrentTile:
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
        self.tempF = 0.0
        self.feelsLike = 0.0
        self.high = 0.0
        self.low = 0.0
        self.humidity = 0.0
        self.windSpeed = 0.0
        self.windDirection = "N/A"
        self.condition = "Error"
        self.icon = None
        self.serviceError = False
        self.updateWeatherCurrent()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherCurrent)
        self.timer.start()

    def updateWeatherCurrent(self):
        try:
            resp = requests.get("https://api.openweathermap.org/data/2.5/weather?id=" +
                                cfg["openWeatherCityID"] +
                                "&APPID=" +
                                cfg["openWeatherAPIKey"])
            self.weather = json.loads(resp.text)
        except Exception:
            # on any exception while fetching or parsing data,
            # leave stale data but set a flag to show that it's stale
            self.serviceError = True
        else:
            self.tempF = kelvinToF(self.weather["main"]["temp"])
            self.feelsLike = kelvinToF(self.weather["main"]["feels_like"])
            self.high = kelvinToF(self.weather["main"]["temp_max"])
            self.low = kelvinToF(self.weather["main"]["temp_min"])
            self.humidity = self.weather["main"]["humidity"]
            self.windSpeed = self.weather["wind"]["speed"]
            self.windDirection = bearingToDir(self.weather["wind"]["deg"])
            self.condition = self.weather["weather"][0]["main"]
            self.icon = "images/openweather/" + \
                        self.weather["weather"][0]["icon"] + \
                        "@2x.png"
            self.serviceError = False

    def render(self):
        image, draw = newTileImage(self.backgroundColor, self.backgroundImage)
        # top text
        text = "Current Weather"
        topSize = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (topSize[0] / 2),
                   10),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # bottom text
        text = ("%.0f F and %s\nHigh: %.0f Low: %.0f\nHumidity: %.0f%%\n"
                "Feels like: %.0f F\nWind: %s at %.0f mph") % \
               (self.tempF,
                self.condition,
                self.high,
                self.low,
                self.humidity,
                self.feelsLike,
                self.windDirection,
                self.windSpeed)
        bottomSize = draw.textsize(text, font=self.font)
        draw.text(((cfg["tileSizeLarge"] / 2) - (bottomSize[0] / 2),
                   (cfg["tileSizeLarge"] - bottomSize[1] - 10)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # icon
        if self.icon is not None:
            with Image.open(self.icon).resize((250, 250), resample=configuration.resizeFilter) \
                as icon:
                image.paste(icon,
                            (int(cfg["tileSizeLarge"] / 2) - 125,
                             int(((cfg["tileSizeLarge"] - topSize[1] - bottomSize[1] - 20) / 2)
                                 + topSize[1] - 115)),
                            mask=icon)
        # error indicator
        if self.serviceError:
            draw.text((0, 0), "X", font=self.font, fill="red")
        return image

#class WeatherForecastTile(object):
#    def __init__(self):
#
#    def renderLarge(self, parentWidget):
#
#    def renderSmall(self, parentWidget):
