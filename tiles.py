from guizero import Text, Picture, Box
from threading import Timer
import requests
import json

# thanks, StackOverflow!
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

class TextTile(object):
    def __init__(self,
                 text="TILE",
                 textColor="white",
                 backgroundColor="black",
                 font="Sans Bold",
                 fontSize=36):
        self.text = text
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.font = font
        self.fontSize = fontSize

    def renderLarge(self, parentWidget):
        foo = Text(parentWidget,
                   text = self.text,
                   color = self.textColor,
                   bg = self.backgroundColor,
                   font = self.font,
                   size = self.fontSize,
                   height = "fill",
                   width = "fill")

    def renderSmall(self, parentWidget):
        foo = Text(parentWidget,
                   text = self.text,
                   color = self.textColor,
                   bg = self.backgroundColor,
                   font = self.font,
                   size = self.fontSize // 2,
                   height = "fill",
                   width = "fill")

class CPUTemperatureTile(object):
    def __init__(self,
                 textColor="white",
                 backgroundColor="black",
                 font="Sans Bold"):
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.font = font

    def getCPUTemp(self):
        with open('/sys/class/thermal/thermal_zone0/temp') as f:
            read = f.read()
        tempC = int(int(read) / 1000)
        tempF = int(tempC * 1.8 + 32)
        return (tempC, tempF)

    def renderLarge(self, parentWidget):
        tempC, tempF = self.getCPUTemp()
        topText = Text(parentWidget,
                       text = "CPU Temp",
                       color = self.textColor,
                       bg = self.backgroundColor,
                       font = self.font,
                       size = 36,
                       width = "fill",
                       height = "fill")
        fill = Box(parentWidget, width = "fill", height = "fill")
        fill.bg = self.backgroundColor
        icon = Picture(fill,
                       image = "images/thermometer.png",
                       width = 150,
                       height = 150)
        icon.bg = self.backgroundColor
        bottomText = Text(parentWidget,
                          text = str(tempC) + " C / " + str(tempF) + " F",
                          color = self.textColor,
                          bg = self.backgroundColor,
                          font = self.font,
                          size = 36,
                          width = "fill",
                          height = "fill")

    def renderSmall(self, parentWidget):
        tempC, tempF = self.getCPUTemp()
        topText = Text(parentWidget,
                       text = "CPU Temp",
                       color = self.textColor,
                       bg = self.backgroundColor,
                       font = self.font,
                       size = 12,
                       width = "fill",
                       height = "fill")
        bottomText = Text(parentWidget,
                          text = str(tempC) + " C / " + str(tempF) + " F",
                          color = self.textColor,
                          bg = self.backgroundColor,
                          font = self.font,
                          size = 12,
                          width = "fill",
                          height = "fill")

class WeatherCurrentTile(object):
    def __init__(self,
                 cfg,
                 textColor="white",
                 backgroundColor="black",
                 font="Sans Bold"):
        self.cfg = cfg
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.font = font
        self.updateWeatherCurrent()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherCurrent)
        self.timer.start()

    def updateWeatherCurrent(self):
        r = requests.get("https://api.openweathermap.org/data/2.5/weather?id=" +
                         self.cfg["openWeatherCityID"] +
                         "&APPID=" +
                         self.cfg["openWeatherAPIKey"])
        #print(r.text) # DEBUG
        self.weather = json.loads(r.text)
        self.tempF = (self.weather["main"]["temp"] - 273.15) * 1.8 + 32 # convert K to F because K is super useful
        self.condition = self.weather["weather"][0]["main"]
        self.icon = "images/openweather/" + \
                    self.weather["weather"][0]["icon"] + \
                    "@2x.png"

    def renderLarge(self, parentWidget):
        topText = Text(parentWidget,
                       text = "Current Weather",
                       color = self.textColor,
                       bg = self.backgroundColor,
                       font = self.font,
                       size = 24,
                       width = "fill",
                       height = "fill")
        fill = Box(parentWidget, width = "fill", height = "fill")
        fill.bg = self.backgroundColor
        icon = Picture(fill,
                       image = self.icon,
                       width = 150,
                       height = 150)
        icon.bg = self.backgroundColor
        bottomText = Text(parentWidget,
                          text = "%.0f F and %s" %
                                 (self.tempF,
                                  self.condition),
                          color = self.textColor,
                          bg = self.backgroundColor,
                          font = self.font,
                          size = 24,
                          width = "fill",
                          height = "fill")

    def renderSmall(self, parentWidget):
        topText = Text(parentWidget,
                       text = "Current Weather",
                       color = self.textColor,
                       bg = self.backgroundColor,
                       font = self.font,
                       size = 12,
                       width = "fill",
                       height = "fill")
        bottomText = Text(parentWidget,
                          text = "%.0f F and %s" %
                                 (self.tempF,
                                  self.condition),
                          color = self.textColor,
                          bg = self.backgroundColor,
                          font = self.font,
                          size = 12,
                          width = "fill",
                          height = "fill")

#class WeatherForecastTile(object):
#    def __init__(self):
#
#    def renderLarge(self, parentWidget):
#
#    def renderSmall(self, parentWidget):
