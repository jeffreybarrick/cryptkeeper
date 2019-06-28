#!/usr/bin/env python

"""
Created on Thu Oct  18 12:26:00 2018
@authors: Alexandra Lukasiewicz 
Purpose: Predict and translate ORF regions in query. 
Code adapted from Biopython 1.72 tutorial and cookbook, 20.1.13
"""

import argparse
import Bio
from Bio import SeqIO
import Bio.Data.CodonTable
from operator import itemgetter
import csv
from CAI import CAI, relative_adaptiveness
import subprocess


#------------------------------------------------------------------------------
parser = argparse.ArgumentParser(description='import fasta for ORF detection')
parser.add_argument('-i',  
    action='store', 
    dest='i',
    required=True,
    type=str,
    help="input using '-i' .fasta file for ORF search")

parser.add_argument('-j',
    action = 'store',
    dest = 'j',
    required = True,
    type = str,
    help = "input using '-j' file for CAI calculations (full sequence)")

parser.add_argument('-t',  
    action='store', 
    dest='t',
    required=False,
    default=11,
    type=str,
    help="set NCBI translation table, default = 11: Bacterial, Archaeal, and Plant Plastids")

parser.add_argument('-l',  
    action='store', 
    dest='l',
    required=False,
    default=30,
    type=str,
    help="set minimum length of protein (in amino acids)")

parser.add_argument('-o', 
    action='store',
    dest= 'o', 
    required=True,
    type=str,
    help="outfile prefix")
#------------------------------------------------------------------------------
options = parser.parse_args()
translation_table_id = options.t #NCBI translation table for Bacterial, Archaeal, and Plant Plastids
minimum_orf_aa_length = options.l 
full_seq = options.j

#subset fasta file into strings to input into CAI
fasta_ref=list(SeqIO.parse(full_seq, "fasta"))
fasta_ref=[str(ele.seq) for ele in fasta_ref]

i=0
for this_seq in SeqIO.parse(options.i, "fasta"):
  i += 1
  if (i>1):
    print("Error: Please input .fasta file with only a single sequence")
    exit()
  main_seq = this_seq.upper()
 #print(this_seq.upper())
 
def find_orfs(seq, translation_table_id, minimum_orf_aa_length):
  orfs = []
  seq_len = len(seq)
  
  #Get the codon table so we know the valid start codons
  translation_table = Bio.Data.CodonTable.unambiguous_dna_by_id[translation_table_id]

  #ignore ultra-rare "UUG" "GUG" start codons (which are not recognized by RBS Calculator)
  if (translation_table_id==11):
    translation_table.start_codons = ['ATG', 'GTG', 'TTG']
  
    #print(translation_table.start_codons)
  
  for this_strand, this_seq in [('+', seq), ('-', seq.reverse_complement())]:
    for start_pos_0 in range(len(this_seq)- 2):
      #print(start_pos_0)
      #print(this_seq[start_pos_0:start_pos_0+3].seq)
      
      #Is this a start codon?
      this_start_codon = this_seq[start_pos_0:start_pos_0+3].seq
      #print(this_start_codon)
      if (this_start_codon not in translation_table.start_codons):
        continue
      start_pos_1 = start_pos_0+1
  
      end_offset = (len(this_seq)-start_pos_1 + 1) % 3
      adjusted_end_pos_1 = len(this_seq) - end_offset

      #print(this_seq[start_pos_0:])
      aa_sequence = this_seq[start_pos_0:adjusted_end_pos_1].seq.translate(translation_table, to_stop=True)
      aa_length = len(aa_sequence)
      
      
      end_pos_1 = start_pos_1 + aa_length*3 - 1
      
      #Is it a long enough reading frame?
      if aa_length < minimum_orf_aa_length:
        continue


      ## Getting codons, is it correct to do start_pos_0:end_pos_1? It gives
      ## a number divisible by three, unlike just start_pos_0:  
      orf_seq = this_seq[start_pos_0:end_pos_1]
      orf_seq = str(orf_seq.seq)

      cai = CAI(sequence = orf_seq, reference = fasta_ref)  

      if (this_strand == '-'):
        start_pos_1 = len(this_seq) - start_pos_1 + 1
        end_pos_1 = len(this_seq) - end_pos_1 + 1
        start_pos_1, end_pos_1 = end_pos_1, start_pos_1

      orfs.append(dict(
        start = start_pos_1, 
        end = end_pos_1,
        strand = this_strand,
        start_codon = this_start_codon,
        length = aa_length,
        cai = cai
        ))
        
  orfs = sorted(orfs, key=itemgetter('start')) 
  return orfs

orfs = find_orfs(main_seq, translation_table_id, minimum_orf_aa_length)

#write each tuple of list to outfile
with open(options.o,'w') as final_predictions_file:
  writer = csv.DictWriter(
      final_predictions_file,
      fieldnames = ["start", "end", "strand", "start_codon", "length", "cai"]
    )

  writer.writeheader()
  writer.writerows(orfs)
final_predictions_file.close()

