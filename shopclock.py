#!/usr/bin/python3

import time
from guizero import App, Box, Text, Picture
from PIL import Image
from tiles import TextTile, CPUTemperatureTile, WeatherCurrentTile, WeatherForecastTile
import configuration

# TODO: eliminate globals

cfg = configuration.cfg

tileSet = []

lastTileImage = None
mainTileImage = None
nextTileImage = None

for tile in cfg["tiles"]:
    if tile["type"] == "Text":
        tileSet.append(TextTile(text=tile.get("text") or None,
                                textColor=tile.get("textColor") or None,
                                backgroundColor=tile.get("backgroundColor") or None,
                                backgroundImage=tile.get("backgroundImage") or None))
    elif tile["type"] == "CPUTemperature":
        tileSet.append(CPUTemperatureTile(textColor=tile.get("textColor") or None,
                                          backgroundColor=tile.get("backgroundColor") or None,
                                          backgroundImage=tile.get("backgroundImage") or None))
    elif tile["type"] == "WeatherCurrent":
        tileSet.append(WeatherCurrentTile(textColor=tile.get("textColor") or None,
                                          backgroundColor=tile.get("backgroundColor") or None,
                                          backgroundImage=tile.get("backgroundImage") or None))
    elif tile["type"] == "WeatherForecast":
        tileSet.append(WeatherForecastTile(textColor=tile.get("textColor") or None,
                                           backgroundColor=tile.get("backgroundColor") or None,
                                           backgroundImage=tile.get("backgroundImage") or None))
    else:
        print("Unrecognized tile type " + tile["type"] + ", skipping.")

def updateTime():
    timeDisplay.value = time.strftime(cfg["timeFormat"])

def updateDate():
    dateDisplay.value = time.strftime(cfg["dateFormat"])

def createTiles():
    global tileBox, currentLastTileIndex, lastTileImage, mainTileImage, nextTileImage
    lastTileImage = tileSet[currentLastTileIndex].render()
    mainTileImage = tileSet[(currentLastTileIndex + 1) % len(tileSet)].render()
    nextTileImage = tileSet[(currentLastTileIndex + 2) % len(tileSet)].render()
    renderTiles()

def renderTiles():
    global tileBox, currentLastTileIndex, lastTileImage, mainTileImage, nextTileImage
    image = Image.new("RGB",
                      (cfg["screenWidth"],
                       cfg["tileSizeLarge"]),
                      color=cfg["backgroundColor"])
    image.paste(lastTileImage.resize((cfg["tileSizeSmall"],
                                      cfg["tileSizeSmall"]),
                                     resample=configuration.resizeFilter),
                (0,
                 int((cfg["tileSizeLarge"] / 2) - (cfg["tileSizeSmall"] / 2))))
    image.paste(mainTileImage,
                (cfg["tileSizeSmall"],
                 0))
    image.paste(nextTileImage.resize((cfg["tileSizeSmall"],
                                      cfg["tileSizeSmall"]),
                                     resample=configuration.resizeFilter),
                (cfg["tileSizeSmall"] + cfg["tileSizeLarge"],
                 int((cfg["tileSizeLarge"] / 2) - (cfg["tileSizeSmall"] / 2))))
    tileBox.image = image
    app.update()

def rotateTiles():
    global tileBox, currentLastTileIndex, lastTileImage, mainTileImage, nextTileImage
    # animate the transition
    onDeckTileImage = tileSet[(currentLastTileIndex + 3) % len(tileSet)].render()
    lastTileSize = float(cfg["tileSizeSmall"])
    mainTileSize = float(cfg["tileSizeLarge"])
    nextTileSize = float(cfg["tileSizeSmall"])
    onDeckTileSize = 0.0
    stepSizeSmall = cfg["tileSizeSmall"] / cfg["animationSteps"]
    stepSizeLarge = (cfg["tileSizeLarge"] - cfg["tileSizeSmall"]) / cfg["animationSteps"]
    for i in range(cfg["animationSteps"]):
        lastTileSize -= stepSizeSmall
        mainTileSize -= stepSizeLarge
        nextTileSize += stepSizeLarge
        onDeckTileSize += stepSizeSmall
        image = Image.new("RGB",
                          (cfg["screenWidth"],
                           cfg["tileSizeLarge"]),
                          color=cfg["backgroundColor"])
        if int(lastTileSize) > 0:
            image.paste(lastTileImage.resize((int(lastTileSize),
                                              int(lastTileSize)),
                                             resample=configuration.resizeFilterFast),
                        (0,
                         int((cfg["tileSizeLarge"] / 2) - (lastTileSize / 2))))
        image.paste(mainTileImage.resize((int(mainTileSize),
                                          int(mainTileSize)),
                                         resample=configuration.resizeFilterFast),
                    (int(lastTileSize),
                     int((cfg["tileSizeLarge"] / 2) - (mainTileSize / 2))))
        image.paste(nextTileImage.resize((int(nextTileSize),
                                          int(nextTileSize)),
                                         resample=configuration.resizeFilterFast),
                    (int(lastTileSize + mainTileSize),
                     int((cfg["tileSizeLarge"] / 2) - (nextTileSize / 2))))
        image.paste(onDeckTileImage.resize((int(onDeckTileSize),
                                            int(onDeckTileSize)),
                                           resample=configuration.resizeFilterFast),
                    (int(lastTileSize + mainTileSize + nextTileSize),
                     int((cfg["tileSizeLarge"] / 2) - (onDeckTileSize / 2))))
        tileBox.image = image
        app.update()
    # update the tile references
    lastTileImage.close()
    lastTileImage = mainTileImage
    mainTileImage = nextTileImage
    nextTileImage = onDeckTileImage
    # update the tile index
    currentLastTileIndex = (currentLastTileIndex + 1) % len(tileSet)
    # render one last time so the non-animated image has the good resampling filter
    renderTiles()

app = App(title="shopclock", bg=cfg["backgroundColor"], layout="auto")

# TOP BAND SETUP
if cfg["topBandHeight"] > 0:
    topBand = Box(app,
                  width=cfg["screenWidth"],
                  height=cfg["topBandHeight"],
                  layout="auto",
                  align="top")
    timeDisplay = Text(topBand,
                       size=18,
                       color=cfg["timeDateColor"],
                       bg=cfg["timeDateBackgroundColor"],
                       font=cfg["timeDateFont"],
                       align="left",
                       text="timeGoesHere",
                       width="fill",
                       height="fill")
    updateTime()
    timeDisplay.repeat(200, updateTime)
    dateDisplay = Text(topBand,
                       size=18,
                       color=cfg["timeDateColor"],
                       bg=cfg["timeDateBackgroundColor"],
                       font=cfg["timeDateFont"],
                       align="right",
                       text="dateGoesHere",
                       width="fill",
                       height="fill")
    updateDate()
    dateDisplay.repeat(10000, updateDate)

# TILE AREA SETUP
tileBox = Picture(app,
                  width=cfg["screenWidth"],
                  height=cfg["tileSizeLarge"],
                  align="top")
currentLastTileIndex = 0
createTiles()
app.repeat(cfg["tileRefreshTime"] * 1000, rotateTiles)

# BOTTOM BAND SETUP
if cfg["bottomBandHeight"] > 0:
    bottomBand = Box(app,
                     width=cfg["screenWidth"],
                     height=cfg["bottomBandHeight"],
                     layout="auto",
                     align="bottom")

# APP DISPLAY
app.set_full_screen()
app.display()
