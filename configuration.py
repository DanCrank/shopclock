#!/usr/bin/python3

import yaml
from PIL import Image

cfg = yaml.safe_load(open("shopclock-config.yaml"))

resizeFilter = Image.BICUBIC
resizeFilterFast = Image.NEAREST
