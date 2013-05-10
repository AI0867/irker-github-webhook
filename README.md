irker-github-webhook
====================
An HTTP server that listens to GitHub webhook POSTs, filters them, processes them into IRC messages and passes them on to irkerd.

irker-github-webhook.py
-----------------------
The server.

update-ips.py
-------------
Updates config.json's "ips" list with the IPs the github hooks currently use, as provided by the GitHub API.

config.json
------------------
Configuration file

* ips: list of CIDR-notation IPs that are allowed to use this server
* port: port to listen on
* targets: dict of URLs (what the POST is submitted to) to target dicts:
    + project: must match the github organization name (or username, if personal repository)
    + channels: dict of email addresses or '\*' to lists of channels
