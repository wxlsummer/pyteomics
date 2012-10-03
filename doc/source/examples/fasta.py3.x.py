import os
from urllib.request import urlretrieve
import matplotlib.pyplot as plt
import numpy as np
from pyteomics import fasta, parser, mass, achrom, electrochem
import gzip
import shelve

# use a persistent dictionary to store the calculation results
data = shelve.open('tmp.shlv', protocol=2)

if 'peptides' not in data:
    if not os.path.isfile('yeast.fasta.gz'):
        print('Downloading the FASTA file for Yeast...')
        urlretrieve(
                'ftp://ftp.uniprot.org/pub/databases/uniprot/'
                'current_release/knowledgebase/proteomes/YEAST.fasta.gz',
            'yeast.fasta.gz')
        print('Done!')

    print('Cleave the proteins with Lys-C...')
    unique_peptides = set()
    for description, sequence in fasta.read(gzip.open('yeast.fasta.gz')):
        new_peptides = []
        for pep in parser.cleave(sequence, parser.expasy_rules['lysc']):
            try:
                parser.parse(pep)
            except PyteomicsError:
                # the sequence may contain unknown residues
                # designated with 'X', etc.
                pass
            else:
                new_peptides.append(pep)
        unique_peptides.update(new_peptides)
    print('Done, {0} sequences obtained!'.format(len(unique_peptides)))

    peptides = [{'sequence': i} for i in unique_peptides]

    print('Parsing peptide sequences...')
    for peptide in peptides:
        peptide['parsed_sequence'] = parser.parse(
            peptide['sequence'],
            show_unmodified_termini=True)
        peptide['length'] = len(peptide['parsed_sequence']) - 2 
    print('Done!')

    peptides = [peptide for peptide in peptides if peptide['length'] <= 200]

    print('Calculating the mass, charge and m/z...')
    for peptide in peptides:
        peptide['mass'] = mass.calculate_mass(peptide['parsed_sequence'])
        peptide['charge'] = int(round(electrochem.charge(peptide['parsed_sequence'], 2.0)))
        peptide['m/z'] = mass.calculate_mass(peptide['parsed_sequence'], 
            charge=peptide['charge'])
    print('Done!')

    print('Calculating the retention time...')
    for peptide in peptides:
        peptide['RT_RP'] = achrom.calculate_RT(
            peptide['parsed_sequence'],
            achrom.RCs_zubarev)
        peptide['RT_normal'] = achrom.calculate_RT(
            peptide['parsed_sequence'],
            achrom.RCs_yoshida_lc)
    print('Done!')

    data['peptides'] = peptides
else:
    peptides = data['peptides']

plt.figure()
plt.hist([peptide['m/z'] for peptide in peptides],
    bins = 250,
    range=(0, 5000.0))
plt.xlabel('m/z, Th')
plt.ylabel('# of peptides within 2 Th bin')

plt.figure()
plt.hist([peptide['charge'] for peptide in peptides],
    bins = 40,
    range=(0,20))
plt.xlabel('charge, e')
plt.ylabel('# of peptides')

x = [peptide['RT_RP'] for peptide in peptides]
y = [peptide['RT_normal'] for peptide in peptides]
heatmap, xbins, ybins = np.histogram2d(x, y, bins=100)

plt.figure()
plt.imshow(heatmap)
plt.xlabel('Retention time (normal phase), min')
plt.ylabel('Retention time (reversed phase), min')
plt.colorbar()
plt.show()

