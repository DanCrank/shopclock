#!/usr/bin/python3

import time
import yaml
from guizero import App, Box, Text
from tiles import TextTile, CPUTemperatureTile, WeatherCurrentTile

cfg = yaml.safe_load(open("shopclock-config.yaml"))

tileSet = []
tileSet.append(WeatherCurrentTile(cfg, textColor = "blue", backgroundColor = "white"))
tileSet.append(CPUTemperatureTile(textColor = "blue", backgroundColor = "white"))
tileSet.append(TextTile(text = "RED", backgroundColor = "#800000"))
tileSet.append(TextTile(text = "BLUE", backgroundColor = "#000080"))
#tileSet.append(TextTile(text = "GREEN", backgroundColor = "#008000"))

def updateTime():
    timeDisplay.value = time.strftime(cfg["timeFormat"])

def updateDate():
    dateDisplay.value = time.strftime(cfg["dateFormat"])

def createTileAreas():
    global lastTileArea, mainTileArea, nextTileArea
    lastTileArea = Box(app,
                       grid = [0,2],
                       width = 180,
                       height = 180,
                       layout = "auto",
                       align = "left")
    mainTileArea = Box(app,
                       grid = [1,1,1,3],
                       width = 400,
                       height = 400,
                       layout = "auto")
    nextTileArea = Box(app,
                       grid = [2,2],
                       width = 180,
                       height = 180,
                       layout = "auto",
                       align = "right")

def destroyTileAreas():
    global lastTileArea, mainTileArea, nextTileArea
    if lastTileArea is not None: lastTileArea.destroy()
    if mainTileArea is not None: mainTileArea.destroy()
    if nextTileArea is not None: nextTileArea.destroy()

def rotateTiles():
    global currentLastTile, tileSet
    currentLastTile = currentLastTile + 1
    if (currentLastTile >= len(tileSet)):
        currentLastTile = 0
    renderTiles()

def renderTiles():
    global currentLastTile, tileSet
    destroyTileAreas()
    createTileAreas()
    tileSet[currentLastTile].renderSmall(lastTileArea)
    tileSet[(currentLastTile + 1) % len(tileSet)].renderLarge(mainTileArea)
    tileSet[(currentLastTile + 2) % len(tileSet)].renderSmall(nextTileArea)
 
app = App(title="shopclock", bg = cfg["backgroundColor"], layout = "grid")

# TOP BAND SETUP
topBand = Box(app,
              grid = [0,0,3,1],
              width = 800,
              height = 40,
              layout = "auto")

timeDisplay = Text(topBand,
                   size = 18,
                   color = cfg["timeDateColor"],
                   bg = cfg["timeDateBackgroundColor"],
                   font = cfg["timeDateFont"],
                   align = "left",
                   text = "timeGoesHere",
                   width = "fill",
                   height = "fill")
updateTime()
timeDisplay.repeat(200, updateTime)

dateDisplay = Text(topBand,
                   size = 18,
                   color = cfg["timeDateColor"],
                   bg = cfg["timeDateBackgroundColor"],
                   font = cfg["timeDateFont"],
                   align = "right",
                   text = "dateGoesHere",
                   width = "fill",
                   height = "fill")
updateDate()
dateDisplay.repeat(10000, updateDate)

# TILE AREA SETUP
lastTileArea = None
mainTileArea = None
nextTileArea = None
currentLastTile = 0
renderTiles()
app.repeat(cfg["tileRefreshTime"] * 1000, rotateTiles)

# BOTTOM BAND SETUP
topBand = Box(app,
              grid = [0,4,3,1],
              width = 800,
              height = 40,
              layout = "auto")

# APP DISPLAY
app.set_full_screen()
app.display()
