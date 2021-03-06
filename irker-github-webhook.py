#!/usr/bin/python3

import cidr
import http.client
import http.server
import json
import posixpath
import socket
import traceback
import urllib.parse

CONFIG_FILE = "config.json"
CONFIG = json.load(open(CONFIG_FILE))

IRKER_PORT = 6659

def shorten(url):
    try:
        con = http.client.HTTPConnection("git.io")
        con.request("POST", "", "url={url}".format(url=url))
        resp = con.getresponse()
        if resp.status == 201:
            url = dict(resp.getheaders()).get("Location", url)
        else:
            print("git.io returned status: {}".format(resp.status))
        con.close()
    except:
        traceback.print_exc()
    return url

def file_list(com):
    filelist = com["modified"] + com["added"] + com["removed"]
    filelist = sorted(set(filelist))
    if len(filelist) == 1:
        return filelist[0]
    prefix = posixpath.commonprefix(filelist).rpartition("/")[0] + "/"
    suffixes = [entry[len(prefix):] for entry in filelist]
    sufstring = " ".join(suffixes)
    if len(sufstring) < 80:
        if prefix == "/":
            return " ".join(filelist)
        else:
            return "{pre} ({suf})".format(pre=prefix, suf=sufstring)
    dirs = len({suffix.rpartition("/")[0] for suffix in suffixes})
    if dirs == 1:
        return "{pre} ({nfiles} files)".format(pre=prefix, nfiles=len(suffixes))
    else:
        return "{pre} ({nfiles} files in {ndirs} dirs)".format(pre=prefix, nfiles=len(suffixes), ndirs=dirs)

COLORS = {'reset': '\x0f', 'yellow': '\x0307', 'green': '\x0303', 'bold': '\x02', 'red': '\x0305'}

def format_commit(everything, commit):
    short_url = shorten(commit["url"])
    files = file_list(commit)
    message = commit["message"].split("\n")[0][:80]
    return "{bold}{project}:{reset} {green}{author}{reset} {repo}:{yellow}{branch}{reset} {bold}{sha}{reset} / {bold}{files}{reset}: {msg} {red}{url}{reset}".format(
        project=everything["repository"]["owner"]["name"],
        repo=everything["repository"]["name"],
        branch=everything["ref"].split("/")[-1],
        author=commit["author"]["name"],
        sha=commit["id"][:12],
        files=files,
        msg=message,
        url=short_url,
        **COLORS)

def format_tag(everything):
    return "{bold}{project}:{reset} {green}{pusher}{reset} {repo}: {bold}{sha}{reset} tagged as {yellow}{tag}{reset}".format(
        project=everything["repository"]["owner"]["name"],
        repo=everything["repository"]["name"],
        pusher=everything["pusher"]["name"],
        tag=everything["ref"].split("/")[-1],
        sha=everything["head_commit"]["id"][:12],
        **COLORS)

def target_channels(target, commit):
    chans = []
    email = commit["author"]["email"]
    if "*" in target["channels"]:
        chans += target["channels"]["*"]
    if email in target["channels"]:
        chans += target["channels"][email]
    return chans

def send_to_irker(message, channels):
    print("{chans}: {msg}".format(chans=",".join(channels), msg=message))
    envelope = { "to": channels, "privmsg": message }
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(json.dumps(envelope).encode("utf-8"), ("localhost", IRKER_PORT))

def process_blob(blob, target):
    for commit in blob["commits"]:
        try:
            message = format_commit(blob, commit)
            channels = target_channels(target, commit)
            send_to_irker(message, channels)
        except:
            traceback.print_exc()
    if blob["ref"].startswith("refs/tags"):
        try:
            message = format_tag(blob)
            fake_commit = {"author":blob["pusher"]} #TODO: factor this properly
            channels = target_channels(target, fake_commit)
            send_to_irker(message, channels)
        except:
            traceback.print_exc()

def check_peer(peer):
    address = cidr.CIDR(peer)
    masks = [cidr.CIDR(ip) for ip in CONFIG["ips"]]
    matches = [address in mask for mask in masks]
    return any(matches)

class Handler(http.server.BaseHTTPRequestHandler):
    def grab_json(self):
        rawblob = self.rfile.read(int(self.headers["content-length"]))
        utf8blob = rawblob.decode("utf-8")
        if self.headers["content-type"] == "application/x-www-form-urlencoded":
            query = urllib.parse.parse_qsl(utf8blob)
            if len(query) == 1 and query[0][0] == "payload":
                return json.loads(query[0][1])
        elif self.headers["content-type"] == "application/json":
            return json.loads(utf8blob)
        else:
            print("Invalid content-type: {}".format(self.headers["content-type"]))
        return None
    def do_POST(self):
        if check_peer(self.client_address[0]):
            target = CONFIG["targets"].get(self.path)
            if target:
                self.connection.settimeout(1) # Don't hang forever.
                jsonblob = self.grab_json()
                if jsonblob:
                    if target["project"] == jsonblob["repository"]["owner"]["name"]:
                        process_blob(jsonblob, target)
                    else:
                        print("Project mismatch {} {}".format(target["project"], jsonblob["repository"]["owner"]["name"]))
                else:
                    print("No payload")
            else:
                print("No target found for {}".format(self.path))
        else:
            print("Not GitHub: {}".format(self.client_address[0]))
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    import sys
    server = http.server.HTTPServer(("", CONFIG["port"]), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
