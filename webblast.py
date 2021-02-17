import time
import re
import requests
import os
import pickle
import sys
from html.parser import HTMLParser

def cache_load():
    session = requests.Session()
    home = os.path.expanduser("~")
    cookie_path = os.path.join(home, ".cache/webblast.cookies")
    if not os.path.exists(cookie_path):
        open(cookie_path, "w").close()
        return session
    else:
        with open(cookie_path, "rb") as f:
            session.cookies.update(pickle.load(f))
        return session

def cache_update(session):
    home = os.path.expanduser("~")
    cookie_path = os.path.join(home, ".cache/webblast.cookies")
    with open(cookie_path, "wb") as f:
        pickle.dump(session.cookies, f)
    return

def submit(blastcmd, query_string, db, cache = False, evalue = None, maxN = None):
    if cache is True:
        session = cache_load()
    else:
        session = requests.Session()

    if blastcmd == "megablast":
        blastcmd = "blastn&MEGABLAST=on"
    args = {"CMD": "Put", "PROGRAM": blastcmd, "DATABASE": db, "QUERY": query_string}
    if evalue is not None:
        args["EXPECT"] = evalue
    if maxN is not None:
        args["ALIGNMENTS"] = maxN
        args["DESCRIPTIONS"] = maxN

    req = session.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", data=args)

    match = re.search("RID = (.{11})", req.text)
    if match is None:
        print(req.text)
        err = re.search("Error: ([^<]*)", req.text).group(1)
        sys.exit(err)
    RID = match.group(1)

    if cache is True:
        cache_update(session)
    return RID

# Add more output .info for the READY runs
def status(RID):
    resp = requests.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", data={"CMD": "Get", "FORMAT_TYPE": "HTML", "RID": RID})
    class status_obj:
        def __init__(self, response, RID):
            self.status = re.search("Status=(.*)", response.text).group(1)
            self.RID = RID
            if self.status == "WAITING":
                self.code = 5
                sd = re.search("Submitted at.*(\w{3} \w{3} \d{2} [\d:]{8} \d{4})", response.text).group(1)
                tss = re.search("Time since submission.*([\d:]{8})", response.text).group(1)
                self.info = {"time_since_submission": tss, "submission_date": sd, "output": "Job is still running"}
            elif self.status == "READY":
                self.code = 0
                self.info = {"output": "Job is finished, access at " + self.RID}
            elif self.status == "UNKNOWN":
                self.code = 3
                self.info = {"output": "Job has either expired, or the RID is wrong"}
            elif self.status == "FAILED":
                err = re.findall("alert-text\">([^<]*)", response.text)
                # print(err)
                if err is None:
                    self.info = {"output": "Search has failed for an unknown reason"}
                else:
                    self.info = {"output": "Search has failed: " + err[-1]}
                # self.info = {"output": "Search has failed;"}
                self.code = 4
            else:
                self.info = {"output": "Unknown error!"}
                self.code = 1
        def __str__(self):
            if self.code == 0:
                return " | ".join(["Job: " + self.RID, "Status: " + self.status])
            elif self.code == 5:
                return "\n".join(["Job: " + self.RID, \
                "Status: " + self.status, \
                "Submission Date: " + self.info["submission_date"], \
                "Time since submission: " + self.info["time_since_submission"]])
            else:
                return " | ".join([self.RID, "Status: " + self.status, self.info["output"]])
    return status_obj(resp, RID)

# For right now, only fmt 1 and 6 are supported
# You also have to clean up the output so it loses the beginning and end formatting
def retrieve(RID, outfmt, maxN = None, outfile = None):
    data_dict = {"CMD": "Get", "RID": RID}

    # if n_align is not None:
    #     data_dict["ALIGNMENTS"] = n_align
    #     data_dict["DESCRIPTIONS"] = n_align
    if outfmt == 1:
        data_dict["FORMAT_TYPE"] = "Text"
        resp = requests.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", data=data_dict)
        # retxt = resp.text.replace("<p><!--\nQBlastInfoBegin\n\tStatus=READY\nQBlastInfoEnd\n--><p>\n<PRE>\n", "") # ew
    elif outfmt == 6:
        data_dict["FORMAT_TYPE"] = "Tabular"
        resp = requests.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", data=data_dict)
        #print(resp)
    else:
        raise ValueError("{} is not a valid outfmt; only 1 and 6 are currently supported :(".format(format))
        return -1

    # Filter to print a certain number of hits, once AGAIN the blast API option for this doesn't work so I've hacked it
    text = resp.text.replace("<p><!--\nQBlastInfoBegin\n\tStatus=READY\nQBlastInfoEnd\n--><p>\n<PRE>\n", "")
    if outfile is None:
        f = sys.stdout
    else:
        f = open(outfile, "w")
    if maxN is None:
        print(text, file = f)
        return
    if outfmt == 1:
        count = 0
        countstart = None
        to_print = True
        for line in text.split("\n"):
            if countstart is not None:
                if line.startswith(countstart) and line != "":
                    count += 1
            if "Sequences producing significant alignments" in line:
                countstart = ""
            if "ALIGNMENTS" in line:
                to_print = True
                countstart = ">"
                count = 0
            if "Database: " in line:
                count = 0
                countstart = None
                to_print = True
            if count > maxN:
                to_print = False
            if to_print is True:
                print(line, file=f)
    elif outfmt == 6:
        count = 0
        for line in text.split("\n"):
            if count <= maxN:
                count += 1
                print(line, file = f)
    f.close()

# This method calls status every 5 seconds while printing updates,
# then calls retrieve if the status is READY
def monitor(RID, outfmt = 6):
    while True:
        stat = status(RID)
        if stat.code == 5:
            time.sleep(5)
            print("\rStatus: " + stat.status + "\tTime since submission: " + stat.info["time_since_submission"], end = "")
            #stat.print()
        elif stat.code == 0:
            #status.print()
            print(retrieve(RID, outfmt))
            return
        else:
            sys.exit("Error " + str(stat.code) + ": " + stat.status)

def list_jobs():
    # custom html parser
    class MyHTMLParser(HTMLParser):
        table = False
        take = None
        n = 0
        dict = {"c0": "Submitted at", "c1": "Request ID", "c2": "Status",\
                "c3": "Program", "c4": "Title", "c5": "Qlength",\
                "c6": "Database", "c7": "Expires at"}
        list = [dict]
        def handle_starttag(self, tag, attrs):
            if self.table:
                if tag == "td":
                    x = attrs[0][1][:2]
                    if x != "cL":
                        self.take = x
            elif tag == "table":
                self.table = True
        def handle_endtag(self, tag):
            if tag == "table":
                self.table = False
        def handle_data(self, data):
            if (self.table and self.take) and (data != " "):
                if self.take == "c0":
                    self.n += 1
                    self.list.append(self.dict.copy())
                if self.take != "c1":
                    self.list[self.n][self.take] = data.rstrip("\n")
                    self.take = None
                elif data != "\n":
                    self.list[self.n][self.take] = data
                    self.take = None
        def custom_print(self, tsv = False):
            if tsv:
                for i in self.list:
                    print(*i.values(), sep = "\t")
            else:
                #maybe make it a bit more advanced so the short ones can have less space alotted
                for i in self.list:
                    print(*["{:15.15}".format(x) for x in i.values()])

    session = cache_load()
    resp = session.post("https://blast.ncbi.nlm.nih.gov/blast/Blast.cgi", data={"CMD": "GetSaved", "RECENT_RESULTS": "on"})
    hparser = MyHTMLParser()
    hparser.feed(resp.text)
    hparser.custom_print()
    return
