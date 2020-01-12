from threading import Timer
import logging
import pygame
import configuration
from utils import getFont, placeTile, tupleColor, getCPUTemp, flattenString, RepeatTimer

cfg = configuration.cfg


class Tile:
    def __init__(self, tile):
        self.textColor = tupleColor(tile.get("textColor")) or tupleColor("#FFFFFF")
        self.backgroundColor = tupleColor(tile.get("backgroundColor")) or tupleColor("#000000")
        self.backgroundImageName = tile.get("backgroundImage") or None
        if self.backgroundImageName is not None:
            self.backgroundImage = pygame.transform.smoothscale(pygame.image.load("images/" + self.backgroundImageName).convert(),
                                                                (cfg["tileSizeLarge"],
                                                                 cfg["tileSizeLarge"]))
        else:
            self.backgroundImage = None
        self.fontName = tile.get("font") or "Ubuntu-Regular"
        self.fontSize = tile.get("fontSize") or 36
        self.font = getFont(self.fontName, self.fontSize)

    def render(self):
        if self.backgroundImage is None:
            image = pygame.Surface((cfg["tileSizeLarge"], cfg["tileSizeLarge"]))
            image.fill(self.backgroundColor)
        else:
            image = self.backgroundImage.copy()
        return image

    def renderText(self, text, **kwargs):
        font = kwargs.get("font") or self.font
        color = kwargs.get("color") or self.textColor
        flattenedText = flattenString(text)
        if "\n" in flattenedText:
            return self.renderMultilineText(flattenedText.split("\n"), font=font, color=color)
        return font.render(flattenedText, True, color)

    def renderMultilineText(self, lines, **kwargs):
        font = kwargs.get("font") or self.font
        color = kwargs.get("color") or self.textColor
        # render each line
        textImages = []
        height = 0
        width = 0
        for line in lines:
            textImage = self.renderText(line, font=font, color=color)  # trust me
            textImages.append(textImage)
            lineWidth, lineHeight = textImage.get_size()
            height = height + lineHeight
            if lineWidth > width:
                width = lineWidth
        # now stitch them together
        image = pygame.Surface((width, height), pygame.SRCALPHA)
        y = 0
        for textImage in textImages:
            image.blit(textImage, (0, y))
            y = y + textImage.get_height()
        return image

    def renderWrappedText(self, text, wrapWidth, **kwargs):
        # split the string to wrap it to the given width
        # and then pass to renderMultilineText
        # note that this splits strictly on spaces, and
        # preserves any newlines already in the string.
        font = kwargs.get("font") or self.font
        color = kwargs.get("color") or self.textColor
        lines = []
        done = False
        lastLength = -1
        logging.info("Wrapping text to %s pixels:\n%s" %
                     (wrapWidth, text))
        while not done:
            # if lastLength == len(text):
            #    logging.error("Infinite loop!")
            #    return None
            # lastLength = len(text)
            # if text now starts with one or more hard line breaks,
            # render them by putting a " " in the array for each one
            while text.startswith("\n"):
                lines.append(" ")
                text = text[1:]
            # find the longest string that will fit in the width
            width = 0
            firstSpace = None
            secondSpace = None
            logging.info("Seeking: %s" % text)
            while width < wrapWidth and not done:
                # if firstSpace is not None and secondSpace is not None and firstSpace == secondSpace:
                #    logging.error("Infinite loop!!")
                #    return None
                firstSpace = secondSpace
                if firstSpace is not None:
                    secondSpace = text.find(" ", firstSpace + 1)
                else:
                    secondSpace = text.find(" ")
                hardLineBreak = text.find("\n")
                if secondSpace == -1:
                    done = True
                elif hardLineBreak >= 0 and \
                        firstSpace is not None and \
                        hardLineBreak > firstSpace and \
                        hardLineBreak < secondSpace:
                    break
                else:
                    logging.info("Sizing: %s" % text[:secondSpace])
                    width, height = font.size(text[:secondSpace])
                    logging.info("width = %s" % width)
            if done:
                logging.info("End of line.")
                lines.append(text.strip(" "))
            elif hardLineBreak >= 0 and \
                    firstSpace is not None and \
                    hardLineBreak > firstSpace and \
                    hardLineBreak < secondSpace:
                logging.info("Hard line break...")
                # here if we hit a hard line break before a soft break
                # we still need to check to see whether the line will fit
                # if we break it at the hard break
                hbWidth, hbHeight = font.size(text[:hardLineBreak])
                if hbWidth > wrapWidth:
                    # nope
                    logging.info("Broke before hard break.")
                    lines.append(text[:firstSpace].strip(" "))
                    text = text[firstSpace:].strip(" ")
                else:
                    # yup
                    logging.info("Broke at hard break.")
                    lines.append(text[:hardLineBreak].strip(" "))
                    text = text[hardLineBreak:].strip(" ")
            elif firstSpace is None:
                logging.info("Word too long!")
                # here if the first segment is too long to begin with
                # in that case, just add it as is and let it clip off
                lines.append(text[:secondSpace].strip(" "))
                text = text[secondSpace:].strip(" ")
            else:
                logging.info("Soft line break.")
                # here if going to the second space would put us over,
                # so break at the first space
                lines.append(text[:firstSpace].strip(" "))
                text = text[firstSpace:].strip(" ")
            logging.info("Added line: %s" % lines[len(lines) - 1])
        return self.renderMultilineText(lines, font=font, color=color)


class TextTile(Tile):
    def __init__(self, tile):
        super().__init__(tile)
        self.text = tile.get("text") or "TEXT"

    def render(self):
        image = super().render()
        textImage = super().renderText(self.text)
        image.blit(textImage, (int((image.get_width() - textImage.get_width()) / 2),
                               int((image.get_height() - textImage.get_height()) / 2)))
        return image


class CPUTemperatureTile(Tile):
    def __init__(self, tile):
        super().__init__(tile)
        self.icon = pygame.transform.smoothscale(pygame.image.load("images/thermometer.png").convert_alpha(),
                                                 (150, 150))

    def render(self):
        tempC, tempF = getCPUTemp()
        image = super().render()
        # top text
        textImage = super().renderText("CPU Temp")
        image.blit(textImage, (int((image.get_width() - textImage.get_width()) / 2),
                               int(textImage.get_height() + 10)))
        # bottom text
        textImage = super().renderText(str(tempC) + " C / " + str(tempF) + " F")
        image.blit(textImage, (int((image.get_width() - textImage.get_width()) / 2),
                               int(image.get_height() - (2 * textImage.get_height()) - 10)))
        # icon
        image.blit(self.icon,
                   (int(image.get_width() / 2) - 75,
                    int(image.get_height() / 2) - 75))
        return image
