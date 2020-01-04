import array
import time
from datetime import date, datetime, timedelta
import json
from threading import Timer
from PIL import Image, ImageDraw, ImageFont
import requests
from tiles import getFont, newTileImage
import configuration

cfg = configuration.cfg

# thanks, StackOverflow!
class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)

def bearingToDir(bearing):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    return directions[int((bearing + 11.25) / 22.5)]

def forceDayIcon(iconName):
    # force the character before the "@" to be a "d"
    return iconName[0:iconName.index("@") - 1] + "d" + iconName[iconName.index("@"):]

def analyzeConditions(forecast, tonight):
    # in the context of this method, "forecast" is the dict for a single day's forecast
    # "tonight" is a flag to tell this method NOT to force a "day" icon
    conditions = forecast.get("conditions")
    # first look for precip
    precip = False
    for condition in conditions:
        if condition <= 699:
            precip = True
            break
    # now loop again to see which condition appears the most
    forecast["condition"] = -1
    forecast["icon"] = None
    forecast["conditionName"] = "N/A"
    conditionCount = 0
    for i in range(len(conditions)):
        condition = conditions[i]
        if ((conditions.count(condition) > conditionCount) and \
            ((precip == False) or (condition <= 699))):
            forecast["condition"] = condition
            iconName = forecast.get("icons")[i]
            # force a daytime icon unless we're specifically looking at the "tonight" forecast
            if not tonight:
                iconName = forceDayIcon(iconName)
            forecast["icon"] = iconName
            forecast["conditionName"] = forecast.get("conditionNames")[i]
            conditionCount = conditions.count(condition)

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
        # initialize data fields in case the first call to the service
        # fails and they don't get filled in
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
        self.fontSmall = getFont(font, 18)
        self.forecast = [{}, {}, {}, {}, {}, {}]
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
            # the return should contain 5 days of data points, 3 hours apart.
            # bin them up by day, and try to distill the bins into today (day 0), tomorrow
            # (day 1), etc. forecasts.

            # the weird thing is that depending on what time of day we call, the data
            # returned might start with today and go through four days from now (if we
            # call in the morning) or it might start with tomorrow and go through five
            # days from now (if we call in the evening). We handle both cases by making
            # the forecast a six-element array here and throwing out the empty day later.
            forecast = [{}, {}, {}, {}, {}, {}]

            # for each day we're just looking for a high, a low, a range of windspeeds,
            # and a general condition for the day.
            self.forecastDay = date.today()
            for datum in self.weather.get("list"):
                # figure out what day this datum is for
                delta = date.fromtimestamp(datum.get("dt")) - self.forecastDay
                day = delta.days
                if day <= 5:
                    self.collectDatum(forecast[day], datum)

            # (arbitrary) rule for analyzing conditions:
            # we use the code that appears the greatest number of times, BUT
            # if any precipitation codes (<= 699) appear, then we ONLY count precip
            # codes for that day. i.e., even if it only rains from 12:00pm - 3:00pm, that's
            # still a rainy day.
            for day in range(len(forecast)):
                conditions = forecast[day].get("conditions")
                if conditions is None:
                    continue
                # check to see if this is a "tonight" forecast;
                # collect
                if (day == 0) and (time.localtime().tm_hour >= 12):
                    tonight = True
                else:
                    tonight = False
                analyzeConditions(forecast[day], tonight)
            self.forecast = forecast
            self.serviceError = False

    def render(self):
        margin = 10 # padding at top and bottom of tile and between columns
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

        # weirdness: the forecast includes "today" if called in the morning
        # but starts with "tomorrow" if called in the evening. we coped with
        # that during data gathering by building a six-day forecast with one
        # empty day. set the offset here so we disregard the empty day.
        if len(self.forecast[0]) == 0:
            offset = 1
        else:
            offset = 0

        # build a list of forecast strings so we can size them and center vertically
        forecastStrings, maxHeight = self.buildForecastStrings(draw, offset)

        # current arrangement is a row of 3 and then a row of 2
        iconSize = 75
        topRowY = int(topSize[1] + 2 * margin)
        bottomRowY = int(((cfg["tileSizeLarge"] - topRowY) / 2) + topRowY)
        columnWidth = cfg["tileSizeLarge"] / 3
        x = []
        y = []
        # x values for top row
        for day in range(3):
            x.append(int((day * columnWidth) + (margin / 2)))
            y.append(topRowY)
        # hacque: center day 4 between 1 and 2, 5 between 2 and 3
        x.append(int((x[0] + x[1]) / 2))
        y.append(bottomRowY)
        x.append(int((x[1] + x[2]) / 2))
        y.append(bottomRowY)

        # start slapping them up there
        iconOffset = int((columnWidth - iconSize) / 2) # this is an X offset only
        for day in range(5):
            draw.ellipse([x[day] + iconOffset,
                          y[day],
                          x[day] + iconOffset + iconSize,
                          y[day] + iconSize],
                         fill="#B0B0FF")
            # have to apply offset to icon lookup since it's looking back to the "old" array
            iconName = self.forecast[day + offset]["icon"]
            with Image.open(iconName).resize((iconSize, iconSize),
                                             resample=configuration.resizeFilter) \
                    as icon:
                image.paste(icon, (x[day] + iconOffset, y[day]), mask=icon)
            draw.text((x[day], int(y[day] + iconSize + (margin / 2))),
                      forecastStrings[day],
                      font=self.fontSmall,
                      fill=self.textColor)
        # error indicator
        if self.serviceError:
            draw.text((0, 0), "X", font=self.font, fill="red")
        return image

    def collectDatum(self, forecast, datum):
        # in the context of this method, "forecast" is the dict for a single day's forecast
        # handle temperature
        temp = datum.get("main").get("temp") # float, F
        if "highTemp" not in forecast or temp > forecast.get("highTemp"):
            forecast["highTemp"] = temp
        if "lowTemp" not in forecast or temp < forecast.get("lowTemp"):
            forecast["lowTemp"] = temp
        # handle wind speed
        wind = datum.get("wind").get("speed") # float, mph
        if "highWind" not in forecast or wind > forecast.get("highWind"):
            forecast["highWind"] = wind
        if "lowWind" not in forecast or wind < forecast.get("lowWind"):
            forecast["lowWind"] = wind
        # handle condition data by saving them in a list to be analyzed later
        if "conditions" not in forecast:
            # initialize the lists on first use
            forecast["conditions"] = []
            forecast["icons"] = []
            forecast["conditionNames"] = []
        forecast["conditions"].append(datum.get("weather")[0].get("id"))
        forecast["icons"].append("images/openweather/" + \
                                 datum.get("weather")[0].get("icon") + \
                                 "@2x.png")
        forecast["conditionNames"].append(datum.get("weather")[0].get("main"))

    def buildForecastStrings(self, draw, offset):
        # build a list of forecast strings so we can size them and center vertically
        forecastStrings = []
        maxHeight = 0
        for day in range(offset, 6):
            # day[0] should be "today" in the morning and "tonight" in the afternoon
            if day == 0:
                if time.localtime().tm_hour < 12:
                    dayName = "Today"
                else:
                    dayName = "Tonight"
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
        return forecastStrings, maxHeight
