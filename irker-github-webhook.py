#!/usr/bin/python3

import http.client
import http.server
import json
import traceback
import urllib.parse

def shorten(url):
    try:
        con = http.client.HTTPConnection("git.io")
        con.request("POST", "", "url={url}".format(url=url))
        resp = con.getresponse()
        if resp.status == 201:
            url = dict(resp.getheaders()).get("Location", url)
        con.close()
    except:
        traceback.print_exc()
    return url

def file_list(com):
    filelist = com["modified"] + com["added"] + com["removed"]
    filelist = sorted(set(filelist))
    filestring = ",".join(filelist)
    if len(filestring) > 80 and len(filelist) > 1:
        pre = filelist[0]
        for fi in filelist:
            while not fi.startswith(pre):
                pre = pre.rpartition("/")[0]
        filestring = "{prefix}/ ({filenum} files)".format(prefix=pre, filenum=len(filelist))
    return filestring

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
        sha=commit["id"][:6],
        files=files,
        msg=message,
        url=short_url,
        **COLORS)


#Filtering and channel-selection should be done here
def blob_to_irc_msgs(blob):
    msgs = []
    for commit in blob["commits"]:
        try:
            msgs.append(format_commit(blob, commit))
        except:
            traceback.print_exc()
    return msgs

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        #self.connection.settimeout(0) # Don't hang forever. JSON blobs should fit in a single packet
        rawblob = self.rfile.read() if "content-length" not in self.headers else self.rfile.read(int(self.headers["content-length"]))
        utf8blob = rawblob.decode("utf-8") # This shouldn't be necessary, but urllib is flaky in 3.1
        #unquotedblob = urllib.parse.unquote_plus(utf8blob)
        #if unquotedblob.startswith("payload="):
        #    jsonblob = json.loads(unquotedblob[8:])
        query = urllib.parse.parse_qsl(utf8blob)
        if len(query) == 1 and query[0][0] == "payload":
            jsonblob = json.loads(query[0][1])
            msgs = blob_to_irc_msgs(jsonblob)
            for msg in msgs:
                print(msg)
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    import sys
    server = http.server.HTTPServer(("", int(sys.argv[1])), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
