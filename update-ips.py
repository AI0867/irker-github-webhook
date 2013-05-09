#!/usr/bin/python3

import json
import urllib.request

CONFIG_FILE = "config.json"

#github_info = json.load(urllib.request.urlopen("https://api.github.com/meta"))
github_info = json.loads(urllib.request.urlopen("https://api.github.com/meta").read().decode("utf-8"))
config = json.load(open(CONFIG_FILE))
config["ips"] = github_info["hooks"]
json.dump(config, open(CONFIG_FILE, "w"), indent=4, separators=(',',': '))
