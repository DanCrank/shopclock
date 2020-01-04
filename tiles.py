import array
import time
from datetime import date, datetime, timedelta
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
                                cfg["openWeatherAPIKey"] +
                                "&units=imperial")
            self.weather = json.loads(resp.text)
        except Exception:
            # on any exception while fetching or parsing data,
            # leave stale data but set a flag to show that it's stale
            self.serviceError = True
        else:
            self.tempF = self.weather["main"]["temp"]
            self.feelsLike = self.weather["main"]["feels_like"]
            self.humidity = self.weather["main"]["humidity"]
            self.windSpeed = self.weather["wind"]["speed"]
            self.windDirection = bearingToDir(self.weather["wind"]["deg"])
            self.condition = self.weather["weather"][0]["main"]
            self.icon = "images/openweather/" + \
                        self.weather["weather"][0]["icon"] + \
                        "@2x.png"
            self.serviceError = False

    def render(self):
        margin = 10 # padding at top and bottom of tile
        tileSize = cfg["tileSizeLarge"]
        image, draw = newTileImage(self.backgroundColor, self.backgroundImage)
        # top text
        text = "Current Weather"
        topSize = draw.textsize(text, font=self.font)
        draw.text(((tileSize / 2) - (topSize[0] / 2),
                   margin),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # bottom text
        text = ("%.0f F and %s\nHumidity: %.0f%%\n"
                "Feels like: %.0f F\nWind: %s at %.0f mph") % \
               (self.tempF,
                self.condition,
                self.humidity,
                self.feelsLike,
                self.windDirection,
                self.windSpeed)
        bottomSize = draw.textsize(text, font=self.font)
        draw.text(((tileSize / 2) - (bottomSize[0] / 2),
                   (tileSize - bottomSize[1] - margin)),
                  text,
                  font=self.font,
                  fill=self.textColor)
        # icon
        if self.icon is not None:
            iconSize = cfg["defaultIconSize"]
            # draw a blue circle behind the icon
            # for X, just center horizontally
            iconX = int((tileSize / 2) - iconSize / 2)
            # for Y, first calculate the empty space between the text blocks
            emptyY = tileSize - topSize[1] - bottomSize[1] - (2 * margin)
            # then the Y coord is margin + top text size + half the empty space - half the icon size
            iconY = int(margin + topSize[1] + (emptyY / 2) - (iconSize / 2))
            draw.ellipse([iconX, iconY, iconX + iconSize, iconY + iconSize], fill="#B0B0FF")
            with Image.open(self.icon).resize((iconSize, iconSize),
                                              resample=configuration.resizeFilter) \
                    as icon:
                image.paste(icon, (iconX, iconY), mask=icon)
        # error indicator
        if self.serviceError:
            draw.text((0, 0), "X", font=self.font, fill="red")
        return image

class WeatherForecastTile:
    def __init__(self,
                 textColor="white",
                 backgroundColor="black",
                 backgroundImage=None,
                 font="Ubuntu-Regular"):
        self.textColor = textColor
        self.backgroundColor = backgroundColor
        self.backgroundImage = backgroundImage
        self.fontName = font
        self.fontLarge = getFont(font, 36)
        self.fontSmall = getFont(font, 12)
        self.serviceError = False
        self.updateWeatherForecast()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherForecast)
        self.timer.start()

    def updateWeatherForecast(self):
        try:
            resp = requests.get("https://api.openweathermap.org/data/2.5/forecast?id=" +
                                cfg["openWeatherCityID"] +
                                "&APPID=" +
                                cfg["openWeatherAPIKey"] +
                                "&units=imperial")
            self.weather = json.loads(resp.text)
        except Exception:
            # on any exception while fetching or parsing data,
            # leave stale data but set a flag to show that it's stale
            self.serviceError = True
        else:
            # the return should contain data points 3 hours apart, 5 days into the future,
            # bin them up by day, and try to distill the bins into today (day 0), tomorrow
            # (day 1), etc. forecasts.
            # for each day we're just looking for a high, a low, a range of windspeeds,
            # and a general condition for the day.
            forecast = [{}, {}, {}, {}, {}, {}]
            self.forecastDay = date.today()
            for datum in self.weather.get("list"):
                # figure out what day this datum is for
                delta = date.fromtimestamp(datum.get("dt")) - self.forecastDay
                day = delta.days
                if day <= 5:
                    # handle temperature
                    temp = datum.get("main").get("temp") # float, F
                    if "highTemp" not in forecast[day] or temp > forecast[day].get("highTemp"):
                        forecast[day]["highTemp"] = temp
                    if "lowTemp" not in forecast[day] or temp < forecast[day].get("lowTemp"):
                        forecast[day]["lowTemp"] = temp
                    # handle wind speed
                    wind = datum.get("wind").get("speed") # float, mph
                    if "highWind" not in forecast[day] or wind > forecast[day].get("highWind"):
                        forecast[day]["highWind"] = wind
                    if "lowWind" not in forecast[day] or wind < forecast[day].get("lowWind"):
                        forecast[day]["lowWind"] = wind
                    # handle condition by saving it, we'll analyze these later
                    if "conditions" not in forecast[day]:
                        forecast[day]["conditions"] = []
                        forecast[day]["icons"] = []
                        forecast[day]["conditionNames"] = []
                    forecast[day]["conditions"].append(datum.get("weather")[0].get("id"))
                    forecast[day]["icons"].append("images/openweather/" + \
                                                  datum.get("weather")[0].get("icon") + \
                                                  "@2x.png")
                    forecast[day]["conditionNames"].append(datum.get("weather")[0].get("main"))
            # (arbitrary) rule for analyzing conditions:
            # we use the code that appears the greatest number of times, BUT
            # if any precipitation codes (<= 699) appear, then we ONLY count precip
            # codes for that day. i.e., if it only rains from 12:00pm - 3:00pm, that's
            # still a rainy day.
            for day in forecast:
                conditions = day.get("conditions")
                if conditions is None:
                    continue
                # first look for precip
                precip = False
                for condition in conditions:
                    if condition <= 699:
                        precip = True
                        break
                # now loop again to see which condition appears the most
                day["condition"] = -1
                day["icon"] = None
                day["conditionName"] = "N/A"
                conditionCount = 0
                for i in range(len(conditions)):
                    if ((conditions.count(conditions[i]) > conditionCount) and \
                        ((precip == False) or (condition <= 699))):
                        day["condition"] = conditions[i]
                        day["icon"] = day.get("icons")[i]
                        day["conditionName"] = day.get("conditionNames")[i]
                        conditionCount = conditions.count(condition)
            self.forecast = forecast
            self.serviceError = False

    def render(self):
        margin = 10 # padding at top and bottom of tile
        tileSize = cfg["tileSizeLarge"]
        image, draw = newTileImage(self.backgroundColor, self.backgroundImage)
        # top text
        text = "Weather Forecast"
        topSize = draw.textsize(text, font=self.fontLarge)
        draw.text(((tileSize / 2) - (topSize[0] / 2),
                   margin),
                  text,
                  font=self.fontLarge,
                  fill=self.textColor)
        # weirdness: still unclear whether the forecast includes "today" if called
        # in the morning. Until I can tell for sure, we've made an array[6] above
        # where we're assuming either the first or last item is a null dict.
        # figure out which and keep an offset
        if len(self.forecast[0]) == 0:
            offset = 1
        else:
            offset = 0
        # build a list of forecast strings so we can size them and center vertically
        forecastStrings = []
        maxHeight = 0
        for day in range(offset, 6):
            if day == 0:
                dayName = "Today"
            elif day == 1:
                dayName = "Tomorrow"
            else:
                dayName = (self.forecastDay + timedelta(days=day)).strftime("%A")
            forecastString = ("%s:\nHigh: %.0f F\nLow: %.0f F\nWind: %.0f-%.0f mph\n%s" % \
                              (dayName,
                               self.forecast[day]["highTemp"],
                               self.forecast[day]["lowTemp"],
                               self.forecast[day]["lowWind"],
                               self.forecast[day]["highWind"],
                               self.forecast[day]["conditionName"]))
            forecastStrings.append(forecastString)
            size = draw.textsize(forecastString, font=self.fontSmall)
            if size[1] > maxHeight:
                maxHeight = size[1]
        # start slapping them up there
        iconSize = 50
        iconY = int(topSize[1] + 2 * margin)
        textY = int(iconY + iconSize + margin)
        columnWidth = cfg["tileSizeLarge"] / 5
        for day in range(5):
            textX = int((day * columnWidth) + (margin / 2))
            iconX = int(textX + (columnWidth / 2) - (iconSize / 2))
            draw.ellipse([iconX, iconY, iconX + iconSize, iconY + iconSize], fill="#B0B0FF")
            # have to apply offset to icon lookup since it's looking back to the "old" array
            # TODO: fix this so it's less shitty
            with Image.open(self.forecast[day + offset]["icon"]).resize((iconSize, iconSize),
                                                             resample=configuration.resizeFilter) \
                    as icon:
                image.paste(icon, (iconX, iconY), mask=icon)
            draw.text((textX, textY), forecastStrings[day], font=self.fontSmall, fill=self.textColor)
        # error indicator
        if self.serviceError:
            draw.text((0, 0), "X", font=self.font, fill="red")
        return image
