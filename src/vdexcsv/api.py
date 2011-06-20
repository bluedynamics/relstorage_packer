import csv
from collections import OrderedDict

class CSV2VDEX(object):
    
    def __init__(self, name, infile, outfile, 
                 startrow=0, colkey=0, colstartvalue=1, langs=['en'],
                 dialect='excel', delimiter=';', treevocabdelimiter='.'):
        self.name = name
        self.infile = infile
        self.outfile = outfile
        self.startrow = startrow
        self.colkey = colkey
        self.colstartvalue = colstartvalue
        self.langs = langs
        self.delimiter = delimiter
        self.treevocabdelimiter = treevocabdelimiter
        if dialect not in csv.list_dialects():
            raise ValueError, "given csv dialect '%s' is unknown. " % dialect +\
                              "pick one of theses: %s" % csv.list_dialects() 
        self.dialect = dialect
        
    @property
    def _fields(self):
        maxlen = max(self.colstartvalue+len(self.langs), self.colkey+1)
        fields = ['__genkey-%s' % _ for _ in range(0, maxlen)]
        fields[self.colkey] = 'key'
        for idx in range(0, len(self.langs)): 
            if self.colstartvalue+idx == self.colkey:
                raise ValueError, 'key column is in same range as value columns'
            fields[self.colstartvalue+idx] = self.langs[idx]
        return fields 
        
    @property
    def _csvdict(self):
        infile = self.infile
        if isinstance(infile, basestring):
            infile = open(infile, 'r')
        value = csv.DictReader(infile, fieldnames=self._fields,
                               dialect=self.dialect, 
                               delimiter=self.delimiter)
        tree = OrderedDict()
        rowcount = -1
        for item in value:
            rowcount += 1
            if rowcount < self.startrow:
                continue
            parts = item['key'].split(self.treevocabdelimiter)
            length = len(parts)
            branch = tree
            for idx in range(0, length):
                part = parts[idx]
                if idx < length-1:
                    branch = branch[part][0]
                    continue
                values = [item[_] for _ in self.langs]
                branch[part] = OrderedDict(), values
        return tree
    
    @property
    def _vdexxml(self):
        return ''
    
    def __call__(self):
        return ''
                