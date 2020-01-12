from io import BytesIO
import logging
import random
import json
import requests
import pygame
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
        self.query = tile.get("query") or "from:%s"
        self.resultType = tile.get("resultType") or "mixed"
        self.language = tile.get("language") or "en"
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
        # make a deep copy we can remove duds from
        searches = list(self.searches)
        while self.tweet == None:
            # have we been through them all?
            if len(searches) == 0:
                break
            # get a random search from the list
            search = random.choice(searches)
            query = self.query % search
            # get recent tweets for that search
            tweets = []
            searchResults = tweepy.Cursor(self.tweepyAPI.search,
                                          q=query,
                                          lang=self.language,
                                          result_type=self.resultType,
                                          include_entities=True,
                                          count=self.freshness).items(self.freshness)
            for tweet in searchResults:
                tweets.append(tweet)
            if len(tweets) > 0:
                # pick a random tweet
                tweet = random.choice(tweets)
                logging.info("Picked tweet: https://twitter.com/%s/status/%s" %
                             (tweet.user.screen_name,
                              tweet.id_str))
                self.tweet = self.tweepyAPI.get_status(tweet.id)
            else:
                # don't try that one again on this pass
                searches.remove(search)

    def render(self):
        # TODO: account for entities like &amp;
        image = super().render()
        margin = 10  # padding at top and bottom of tile
        width, height = image.get_size()
        if self.tweet is not None:
            if self.tweet.is_quote_status:
                return self.renderQuoteTweet(image)
            # TODO: also check for tweets with images
            author = self.tweet.author
            profilePhoto = None
            authorTextImage = None
            if author is not None:
                # profile photo
                try:
                    resp = requests.get(self.tweet.author.profile_image_url_https)
                    profilePhoto = pygame.image.load(BytesIO(resp.content))
                except Exception as e:
                    logging.info("Exception pulling profile photo from %s" %
                                 self.tweet.author.profile_image_url_https,
                                 exc_info=True)
                # author name
                authorText = "@" + author.screen_name + " (" + author.name + ")"
                authorTextImage = super().renderText(authorText)
            # text of tweet
            text = self.tweet.text
            time = self.tweet.created_at
            if time is not None:
                if not text.endswith("\n"):
                    text = text + "\n"
                text = text + "\n" + time.strftime("%I:%M:%S %p %A %B %d %Y")
            textImage = super().renderWrappedText(text, width - (2 * margin))
            # draw the tweet on the tile
            y = margin
            if author is not None:
                if profilePhoto is not None:
                    image.blit(profilePhoto, (margin, margin))
                    profileWidth, profileHeight = profilePhoto.get_size()
                    image.blit(authorTextImage,
                               (int((1.5 * margin) + profileWidth),
                                int(margin +
                                    (0.5 * min((profileHeight - authorTextImage.get_height()),
                                               0)))))
                    y += max((profileHeight, authorTextImage.get_height())) + margin
                else:
                    image.blit(authorTextImage, (margin, margin))
                    y += authorTextImage.get_height()
            image.blit(textImage, (margin, y))
        else:
            text = self.title + "\n\n(Tweet not found)"
            textImage = super().renderText(text)
            image.blit(textImage, (margin, margin))
        return image

    def renderQuoteTweet(self, image):
        # TODO
        text = self.title + "\n\n(quote tweet NYI)"
        textImage = super().renderText(text)
        image.blit(textImage, (margin, margin))
        return image
