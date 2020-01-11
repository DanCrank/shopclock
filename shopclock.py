#!/usr/bin/python3

import sys
import logging
import time
from threading import Semaphore
import pygame
from tiles import TextTile, CPUTemperatureTile
from weathertiles import WeatherCurrentTile, WeatherForecastTile
from twittertiles import RandomTweetTile
from utils import getFont, placeTile, tupleColor, getCPUTemp, RepeatTimer
import configuration

cfg = configuration.cfg

logLevel = cfg.get("logLevel")
if logLevel is not None:
    if logLevel.lower() == "debug":
        logging.basicConfig(level=logging.DEBUG)
    elif logLevel.lower() == "info":
        logging.basicConfig(level=logging.INFO)


# TODO: allow screen saver correctly


class TileManager:
    def start(self):
        self.renderSemaphore = Semaphore()
        self.tileSet = []
        self.lastTileImage = None
        self.mainTileImage = None
        self.nextTileImage = None

        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)

        for tile in cfg["tiles"]:
            if tile["type"] == "Text":
                self.tileSet.append(TextTile(tile))
            elif tile["type"] == "CPUTemperature":
                self.tileSet.append(CPUTemperatureTile(tile))
            elif tile["type"] == "WeatherCurrent":
                self.tileSet.append(WeatherCurrentTile(tile))
            elif tile["type"] == "WeatherForecast":
                self.tileSet.append(WeatherForecastTile(tile))
            elif tile["type"] == "RandomTweet":
                self.tileSet.append(RandomTweetTile(tile))
            else:
                print("Unrecognized tile type " + tile["type"] + ", skipping.")

        self.currentLastTileIndex = 0
        self.createTiles()
        self.rotateTimer = RepeatTimer(cfg["tileRefreshTime"], self.rotateTiles)
        self.rotateTimer.start()
        self.clockTimer = RepeatTimer(1, self.renderFull)
        self.clockTimer.start()
        while 1:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.stop()
                    sys.exit()
            time.sleep(0.200)

    def stop(self):
        pygame.mouse.set_visible(True)

    def createTiles(self):
        self.lastTileImage = self.tileSet[self.currentLastTileIndex].render()
        self.mainTileImage = self.tileSet[(self.currentLastTileIndex + 1) %
                                          len(self.tileSet)].render()
        self.nextTileImage = self.tileSet[(self.currentLastTileIndex + 2) %
                                          len(self.tileSet)].render()
        self.onDeckTileImage = None
        self.renderFull()

    def renderFull(self):
        # semaphore so we don't glitch the screen in the midst of a transition animation
        self.renderSemaphore.acquire()
        self.render(cfg["tileSizeSmall"], cfg["tileSizeLarge"], cfg["tileSizeSmall"], 0)
        self.renderSemaphore.release()

    def render(self, lastTileSize, mainTileSize, nextTileSize, onDeckTileSize, fast=False):
        self.screen.fill(tupleColor(cfg["backgroundColor"]))
        y = 0
        if (cfg["topBandHeight"] > 0):
            self.drawTopBand(y)
            y = y + cfg["topBandHeight"]
        if (cfg["tileSizeLarge"] > 0):
            self.drawTiles(y, lastTileSize, mainTileSize, nextTileSize, onDeckTileSize)
            y = y + cfg["tileSizeLarge"]
        if (cfg["bottomBandHeight"] > 0):
            self.drawBottomBand(y)
        pygame.display.flip()

    def drawTopBand(self, y):
        self.screen.fill(tupleColor(cfg["timeDateBackgroundColor"]),
                         rect=pygame.Rect(0, y, cfg["screenWidth"], cfg["topBandHeight"] + y))
        font = getFont(cfg["timeDateFont"], int(cfg["topBandHeight"] * 0.9))
        timeImage = font.render(time.strftime(cfg["timeFormat"]),
                                True,
                                tupleColor(cfg["timeDateColor"]),
                                tupleColor(cfg["timeDateBackgroundColor"]))
        self.screen.blit(timeImage, (0, y))
        dateImage = font.render(time.strftime(cfg["dateFormat"]),
                                True,
                                tupleColor(cfg["timeDateColor"]),
                                tupleColor(cfg["timeDateBackgroundColor"]))
        self.screen.blit(dateImage, (int(cfg["screenWidth"] - dateImage.get_width()), y))

    def drawBottomBand(self, y):
        # TODO
        pass

    def drawTiles(self, y, lastTileSize, mainTileSize, nextTileSize, onDeckTileSize, fast=False):
        vc = int(cfg["tileSizeLarge"] / 2) + y  # y coordinate of tilebox center
        if lastTileSize > 0:
            placeTile(self.lastTileImage,
                      self.screen,
                      (lastTileSize, lastTileSize),
                      (0, int(vc - (lastTileSize / 2))),
                      fast)
        placeTile(self.mainTileImage,
                  self.screen,
                  (mainTileSize, mainTileSize),
                  (lastTileSize, int(vc - (mainTileSize / 2))),
                  fast)
        placeTile(self.nextTileImage,
                  self.screen,
                  (nextTileSize, nextTileSize),
                  (lastTileSize + mainTileSize,
                   int(vc - (nextTileSize / 2))),
                  fast)
        if onDeckTileSize > 0 and self.onDeckTileImage is not None:
            placeTile(self.onDeckTileImage,
                      self.screen,
                      (onDeckTileSize, onDeckTileSize),
                      (lastTileSize + mainTileSize + nextTileSize,
                       int(vc - (onDeckTileSize / 2))),
                      fast)

    def rotateTiles(self):
        # semaphore so another timer doesn't glitch the screen in the midst of the animation
        self.renderSemaphore.acquire()
        # animate the transition
        self.onDeckTileImage = self.tileSet[(
            self.currentLastTileIndex + 3) % len(self.tileSet)].render()
        lastTileSize = float(cfg["tileSizeSmall"])
        mainTileSize = float(cfg["tileSizeLarge"])
        nextTileSize = float(cfg["tileSizeSmall"])
        onDeckTileSize = 0.0
        stepSizeSmall = cfg["tileSizeSmall"] / cfg["animationSteps"]
        stepSizeLarge = (cfg["tileSizeLarge"] - cfg["tileSizeSmall"]) / \
            cfg["animationSteps"]
        for i in range(cfg["animationSteps"]):
            lastTileSize -= stepSizeSmall
            mainTileSize -= stepSizeLarge
            nextTileSize += stepSizeLarge
            onDeckTileSize += stepSizeSmall
            self.render(int(lastTileSize),
                        int(mainTileSize),
                        int(nextTileSize),
                        int(onDeckTileSize),
                        fast=True)
        # update the tile references
        self.lastTileImage = self.mainTileImage
        self.mainTileImage = self.nextTileImage
        self.nextTileImage = self.onDeckTileImage
        self.onDeckTileImage = None
        # update the tile index
        self.currentLastTileIndex = (self.currentLastTileIndex + 1) % len(self.tileSet)
        self.renderSemaphore.release()
        # render one last time so the non-animated image has the good resampling filter
        self.renderFull()


if __name__ == '__main__':
    TileManager().start()
