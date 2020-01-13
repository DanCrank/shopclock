import array
import time
from datetime import date, datetime, timedelta
import json
from threading import Semaphore, Timer
import pygame
import requests
import configuration
from tiles import Tile
from utils import getFont, placeTile, tupleColor, getCPUTemp, RepeatTimer

cfg = configuration.cfg


def bearingToDir(bearing):
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "N"]
    return directions[int((bearing + 11.25) / 22.5)]


def forceDayIcon(iconName):
    # force last character to be a "d"
    return iconName[0:len(iconName) - 1] + "d"


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
        if ((conditions.count(condition) > conditionCount) and
                ((precip == False) or (condition <= 699))):
            forecast["condition"] = condition
            iconName = forecast.get("icons")[i]
            # force a daytime icon unless we're specifically looking at the "tonight" forecast
            if not tonight:
                iconName = forceDayIcon(iconName)
            forecast["icon"] = iconName
            forecast["conditionName"] = forecast.get("conditionNames")[i]
            conditionCount = conditions.count(condition)


class WeatherTile(Tile):
    def __init__(self, tile):
        super().__init__(tile)
        self.iconSize = tile.get("iconSize") or 75
        self.icons = {}

    def getIcon(self, name):
        if name in self.icons:
            return self.icons.get(name)
        icon = pygame.transform.smoothscale(pygame.image.load("images/openweather/" + name + "@2x.png").convert_alpha(),
                                            (self.iconSize, self.iconSize))
        self.icons[name] = icon
        return icon


class WeatherCurrentTile(WeatherTile):
    def __init__(self, tile):
        super().__init__(tile)
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
        self.renderSemaphore = Semaphore()
        self.updateWeatherCurrent()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherCurrent)
        self.timer.start()

    def updateWeatherCurrent(self):
        self.renderSemaphore.acquire()
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
            logging.warning("Exception while running OpenWeather query", exc_info=True)
        else:
            self.tempF = self.weather["main"]["temp"]
            self.feelsLike = self.weather["main"]["feels_like"]
            self.humidity = self.weather["main"]["humidity"]
            self.windSpeed = self.weather["wind"]["speed"]
            self.windDirection = bearingToDir(self.weather["wind"]["deg"])
            self.condition = self.weather["weather"][0]["main"]
            self.icon = self.weather["weather"][0]["icon"]
            self.locale = self.weather["name"]
            self.serviceError = False
        finally:
            self.renderSemaphore.release()

    def render(self):
        image = super().render()
        margin = 10  # padding at top and bottom of tile
        width, height = image.get_size()
        self.renderSemaphore.acquire()
        try:
            # top text
            topTextImage = super().renderText("%s Weather" % self.locale)
            topWidth, topHeight = topTextImage.get_size()
            image.blit(topTextImage, (int((width / 2) - (topWidth / 2)),
                                      margin))
            # bottom text
            bottomText = ("%.0f F and %s\nHumidity: %.0f%%\n"
                          "Feels like: %.0f F\nWind: %s at %.0f mph") % \
                (self.tempF,
                 self.condition,
                 self.humidity,
                 self.feelsLike,
                 self.windDirection,
                 self.windSpeed)
            bottomTextImage = super().renderText(bottomText)
            bottomWidth, bottomHeight = bottomTextImage.get_size()
            image.blit(bottomTextImage, (int((width / 2) - (bottomWidth / 2)),
                                         int((height - bottomHeight - margin))))
            # icon
            if self.icon is not None:
                # draw a blue circle behind the icon
                # for X, just center horizontally
                iconX = int((width / 2) - self.iconSize / 2)
                # for Y, first calculate the empty space between the text blocks
                emptyY = height - topHeight - bottomHeight - (2 * margin)
                # then the Y coord is margin + top text size + half the empty space - half the icon size
                iconY = int(margin + topHeight + (emptyY / 2) - (self.iconSize / 2))
                pygame.draw.ellipse(image,
                                    tupleColor("#B0B0FF"),
                                    pygame.Rect(iconX,
                                                iconY,
                                                self.iconSize,
                                                self.iconSize))
                image.blit(self.getIcon(self.icon), (iconX, iconY))
            # error indicator
            if self.serviceError:
                errorIndicator = super().renderText("X", color=tupleColor("#FF0000"))
                image.blit(errorIndicator, (0, 0))
            return image
        finally:
            self.renderSemaphore.release()


class WeatherForecastTile(WeatherTile):
    def __init__(self, tile):
        super().__init__(tile)
        self.fontSmall = getFont(self.fontName, 18)
        self.forecast = [{}, {}, {}, {}, {}, {}]
        self.serviceError = False
        self.renderSemaphore = Semaphore()
        self.updateWeatherForecast()
        self.timer = RepeatTimer(cfg["openWeatherUpdateInterval"], self.updateWeatherForecast)
        self.timer.start()

    def updateWeatherForecast(self):
        self.renderSemaphore.acquire()
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
            logging.warning("Exception while running OpenWeather query", exc_info=True)
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
            self.locale = self.weather.get("city").get("name")
            self.serviceError = False
        finally:
            self.renderSemaphore.release()

    def render(self):
        image = super().render()
        margin = 10  # padding at top and bottom of tile and between columns
        width, height = image.get_size()
        self.renderSemaphore.acquire()
        try:
            # top text
            topTextImage = super().renderText("%s Forecast" % self.locale)
            topWidth, topHeight = topTextImage.get_size()
            image.blit(topTextImage, (int((width / 2) - (topWidth / 2)),
                                      margin))

            # weirdness: the forecast includes "today" if called in the morning
            # but starts with "tomorrow" if called in the evening. we coped with
            # that during data gathering by building a six-day forecast with one
            # empty day. set the offset here so we disregard the empty day.
            if len(self.forecast[0]) == 0:
                offset = 1
            else:
                offset = 0

            # build a list of forecast strings so we can size them and center vertically
            forecastStrings, maxHeight = self.buildForecastStrings(offset)

            # current arrangement is a row of 3 and then a row of 2
            topRowY = int(topHeight + 2 * margin)
            bottomRowY = int(((height - topRowY) / 2) + topRowY)
            columnWidth = width / 3
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
            iconOffset = int((columnWidth - self.iconSize) / 2)  # this is an X offset only
            for day in range(5):
                pygame.draw.ellipse(image,
                                    tupleColor("#B0B0FF"),
                                    pygame.Rect(x[day] + iconOffset,
                                                y[day],
                                                self.iconSize,
                                                self.iconSize))
                # have to apply offset to icon lookup since it's looking back to the "old" array
                image.blit(self.getIcon(self.forecast[day + offset]["icon"]),
                           (x[day] + iconOffset, y[day]))
                forecastTextImage = super().renderText(forecastStrings[day], font=self.fontSmall)
                image.blit(forecastTextImage, (x[day], int(y[day] + self.iconSize + (margin / 2))))
            # error indicator
            if self.serviceError:
                errorIndicator = super().renderText("X", color=tupleColor("#FF0000"))
                image.blit(errorIndicator, (0, 0))
            return image
        finally:
            self.renderSemaphore.release()

    def collectDatum(self, forecast, datum):
        # in the context of this method, "forecast" is the dict for a single day's forecast
        # handle temperature
        temp = datum.get("main").get("temp")  # float, F
        if "highTemp" not in forecast or temp > forecast.get("highTemp"):
            forecast["highTemp"] = temp
        if "lowTemp" not in forecast or temp < forecast.get("lowTemp"):
            forecast["lowTemp"] = temp
        # handle wind speed
        wind = datum.get("wind").get("speed")  # float, mph
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
        forecast["icons"].append(datum.get("weather")[0].get("icon"))
        forecast["conditionNames"].append(datum.get("weather")[0].get("main"))

    def buildForecastStrings(self, offset):
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
            forecastString = ("%s:\nHigh: %.0f F\nLow: %.0f F\nWind: %.0f-%.0f mph\n%s" %
                              (dayName,
                               self.forecast[day]["highTemp"],
                               self.forecast[day]["lowTemp"],
                               self.forecast[day]["lowWind"],
                               self.forecast[day]["highWind"],
                               self.forecast[day]["conditionName"]))
            forecastStrings.append(forecastString)
            width, height = font = self.fontSmall.size(forecastString)
            if height > maxHeight:
                maxHeight = height
        return forecastStrings, maxHeight
