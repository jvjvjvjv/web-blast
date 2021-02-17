import webblast
import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(title = "subcommands", dest = "CMD", help = \
        " | \n".join(["web_blast.py [command]", \
                    "Blast submission commands:" \
                    "blastn, tblastx, megablast, etc..", \
                    "Queue interfacing commands:" \
                    "list, status, get, cancel"]))

    ## Blast submission commands
    b_parser = subparser.add_parser("blastn", aliases = ["blastp", "blastx", "tblastn", "tblastx", "megablast", "rpsblast"])
    b_parser.set_defaults(func=blast)
    b_parser.add_argument("QUERY", help = "fasta file or sequence")
    b_parser.add_argument("-db", help = "If not supplied, a correct database will be chosen based on your blast command")
    b_parser.add_argument("-evalue", help = "e value cutoff")
    b_parser.add_argument("-out", help = "Output file")
    b_parser.add_argument("-outfmt", default = 6, type=int, help="Blast outformats, 1 (text) and 6 (tabular) are supported; Default 6")
    b_parser.add_argument("-bg", action = "store_true", help="When submitting blast job, put it in the background and don't wait for output; returns RID")
    #b_parser.add_argument("-query", help = "Overwrites the main QUERY argument; This is only here to match the blast+ style but it's otherwise pointless")
    b_parser.add_argument("--no-cache", action = "store_true", help = "By default this program saves your cache in ~/.cache/webblast.cookies so you can retrieve results later. This argument disables that")
    b_parser.add_argument("-n", type = int, help="Number of alignments to return")
    #b_parser.add_argument("--never-cache", help = "Toggle caching for future runs")


    ## Interfacing commands
    # list
    l_parser = subparser.add_parser("list")
    l_parser.set_defaults(func=listcmd)
    # this has no args!

    # status
    s_parser = subparser.add_parser("status")
    s_parser.set_defaults(func=statuscmd)
    s_parser.add_argument("RID", help = "The RID associated with your blast run. If you don't know, try web_blast.py list")
    s_parser.add_argument("-out", help="Output file")
    s_parser.add_argument("-monitor", action="store_true", help = "continue monitoring job until it's done. Then downloads")
    s_parser.add_argument("-outfmt", default=6, type=int, help="MUST BE USED WITH -monitor else it will be ignored; Blast outformats, 1 (text) and 6 (tabular) are supported; Default 6")
    #need exclusive groups: outfmt, evalue, etc should work but only if monitor is true

    # get
    g_parser = subparser.add_parser("get")
    g_parser.set_defaults(func=getcmd)
    g_parser.add_argument("RID", help = "The RID associated with your blast run. If you don't know, try web_blast.py list")
    g_parser.add_argument("-out", help="Output file")
    g_parser.add_argument("-outfmt", default=6, type=int, help="Blast outformats, 1 (text) and 6 (tabular) are supported; Default 6")
    g_parser.add_argument("-n", type = int, help="Number of alignments to return")
    # --readable?

    args = parser.parse_args()
    # args.func(args)
    try:
        args.func(args)
    except AttributeError as e:
        print("AttributeError:", e)
        sys.exit("No arguments given: Try web_blast.py -h")


def blast(args):
    # print("blasting", args)
    if args.db is None:
        dbdict = {"blastn": "nt", "blastp": "nr", "blastx": "nr", "tblastx": "nt", "tblastn": "nt", "megablast": "nt"} #add rpsblast/ other options?
        args.db = dbdict[args.CMD]
    # submit blast, and monitor IF args.bg is True
    with open(args.QUERY, "r") as f:
        query = f.read()
    RID = webblast.submit(args.CMD, query, args.db, evalue = args.evalue, cache = not args.no_cache)
    print(RID)
    if not args.bg:
        webblast.monitor(RID, args.outfmt)

def listcmd(args):
    # print("list", args)
    webblast.list_jobs()

def getcmd(args):
    # print("get", args)
    webblast.retrieve(args.RID, args.outfmt, maxN = args.n, outfile = args.out)

def statuscmd(args):
    # print("status", args)
    if args.monitor:
        webblast.monitor(args.RID, outfmt = args.outfmt)
    else:
        print(webblast.status(args.RID))

if __name__ == "__main__":
    main()
