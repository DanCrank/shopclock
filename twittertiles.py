import logging
import random
import json
import requests
import tweepy
import configuration
from tiles import Tile
from utils import getFont, placeTile, tupleColor, getCPUTemp, flattenString, RepeatTimer

cfg = configuration.cfg

# TODO: if a retweet is selected, show who retweeted it
# TODO: (optionally) filter out replies
# TODO: (optionally) filter out retweets
# TODO: display full tweets, not truncated tweets (?)
# TODO: display picture if attached to tweet


class RandomTweetTile(Tile):
    def __init__(self, tile):
        super().__init__(tile)
        self.title = tile.get("title") or "Twitter"
        self.freshness = tile.get("freshness") or 48
        self.lineLength = tile.get("lineLength") or 40
        self.searches = tile.get("searches") or []
        self.tweet = None
        random.seed()
        self.tweepyAuth = tweepy.OAuthHandler(cfg["twitterAPIKey"],
                                              cfg["twitterAPISecretKey"])
        self.tweepyAPI = tweepy.API(self.tweepyAuth)
        self.getANewTweet()
        self.timer = RepeatTimer(cfg["twitterUpdateInterval"], self.getANewTweet)
        self.timer.start()

    def getANewTweet(self):
        self.tweet = None
        retries = 5
        while (self.tweet == None) and (retries > 0):
            retries -= 1
            # get a random search from the list
            search = random.choice(self.searches)
            if search.startswith("@"):
                search = search[1:]
            # get recent tweets for that search
            tweets = []
            searchResults = tweepy.Cursor(self.tweepyAPI.search, q=search,
                                          count=self.freshness).items(self.freshness)
            for tweet in searchResults:
                tweets.append(tweet)
            if len(tweets) > 0:
                # pick a random tweet
                self.tweet = random.choice(tweets)

    def render(self):
        image = super().render()
        margin = 10  # padding at top and bottom of tile
        width, height = image.get_size()
        # draw the tweet on the tile
        text = self.title + "\n\n"
        if self.tweet is not None:
            text = text + self.tweet.text
        author = self.tweet.author
        if author is not None:
            text = text + "\n\n--@" + author.screen_name + " (" + author.name + ")"
        # slap it up there
        textImage = super().renderWrappedText(flattenString(text), width)
        image.blit(textImage, (margin, margin))
        return image
