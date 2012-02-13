import argparse
from vdexcsv import api 

parser = argparse.ArgumentParser(description='Converts CSV files to VDEX XML')
parser.add_argument('--languages', '-l', nargs='?', default='en', 
                    help='Comma separated list of ISO-language codes. ' 
                    'Default: en')
parser.add_argument('--startrow', '-r', nargs='?', type=int, default=0, 
                    help='number of row in CSV file where to begin reading, '
                        'starts with 0, default 0.')
parser.add_argument('--keycolumn', '-k', nargs='?', type=int, default=0, 
                    help='number of column with the keys of the vocabulary, '
                         'start with 0, default 0.')
parser.add_argument('--startcolumn', '-s', nargs='?', type=int, default=1, 
                    help='number of column with the first langstring of the ' 
                         'vocabulary. It assume n + number languages of columns'
                         ' after this, starts counting with 0, default 1.')
parser.add_argument('--ordered', '-o', nargs='?', type=bool, default=True, 
                    help='Wether vocabulary is ordered or not, Default: True')
parser.add_argument('--dialect', nargs='?', default='excel', 
                    help='CSV dialect, default excel.')
parser.add_argument('--csvdelimiter', nargs='?', default=';', 
                    help='CSV delimiter of the source file, default colon.')
parser.add_argument('--treedelimiter', nargs='?', default='.', 
                    help='Delimiter used to split the key the vocabulary into '
                         'a path to determine the position in the tree, '
                         'default dot.')
parser.add_argument('--encoding', '-e', nargs='?', default='utf-8', 
                    help='Encoding of input file. Default: utf-8')
parser.add_argument('id', nargs=1,
                   help='unique identifier of vocabulary')
parser.add_argument('name', nargs=1, 
                   help='Human readable name of vocabulary. If more than one '
                        'language is given separate each langstring by a colon '
                        'and provide same order as argument --languages')
parser.add_argument('source', nargs=1,
                   help='CSV file to read from')
parser.add_argument('target', nargs=1,
                   help='XML target file')

def run():
    ns = parser.parse_args()
    api.CSV2VDEX(ns.id[0], ns.name[0], ns.source[0], ns.target[0], 
                 ns.startrow, ns.keycolumn, ns.startcolumn, ns.languages, 
                 ns.dialect, ns.csvdelimiter, ns.treedelimiter, 
                 ns.ordered, ns.encoding)()