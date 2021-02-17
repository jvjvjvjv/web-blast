# web-blast
NCBI blast searches from the command line with just python

##### [currently incomplete but basic searches still work]

While biopython and BLAST+ offer more features, this script was designed to be trivial to run and to give some visual feedback on search progress in a way that mirrors the web version. It saves a cache allowing you to queue multiple searches in the background and retrieve the results later (NCBI saves results for 24 hours). 

```python
python web-blast.py [blast program] [sequence file]

#examples
python web-blast.py blastn seqs.fasta
python web-blast.py blastx nucl.fa -bg    # runs in background, prints RID
python web_blast.py blastn seq.f --no-cache   # disable caching
python web-blast.py blastp prot.fasta -evalue 1e-10 -outfmt 6 -out output.tsv   # can supply e-value cutoffs and specify out format like BLAST+

#get list of cached searches
python web_blast.py list

#retrieve previous search results
python web_blast.py get [RID] -outfmt 6
```
