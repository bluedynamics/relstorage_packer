import csv
from lxml import etree
from collections import OrderedDict

NSVDEX = 'http://www.imsglobal.org/xsd/imsvdex_v1p0'
NSMAP = {None: NSVDEX}

def vtag(tag):
    return "{%s}%s" % (NSVDEX, tag) 

class CSV2VDEX(object):
    
    def __init__(self, name, infile, outfile, 
                 startrow=0, colkey=0, colstartvalue=1, langs=['en'],
                 dialect='excel', delimiter=';', treevocabdelimiter='.',
                 ordered=True):
        self.name = name
        self.infile = infile
        self.outfile = outfile
        self.startrow = startrow
        self.colkey = colkey
        self.colstartvalue = colstartvalue
        self.langs = langs
        self.delimiter = delimiter
        self.treevocabdelimiter = treevocabdelimiter
        self.ordered = ordered
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
                branch[part] = OrderedDict(), values, item['key']
        return tree
    
    def __call__(self):
        root = etree.Element(vtag("vocabulary"), nsmap=NSMAP) 
        root.attrib['orderSignificant'] = str(self.ordered).lower()
        vid = etree.SubElement(root, vtag('vocabIdentifier'))
        vid.text = self.name
        def treeworker(tree, parent):
            for key in tree:
                subtree, values, longkey = tree[key]
                term = etree.SubElement(parent, vtag('term'))
                termid = etree.SubElement(term, vtag('termIdentifier'))
                termid.text = longkey
                caption = etree.SubElement(term, vtag('caption'))
                for idx in range(0, len(values)):
                    langstring = etree.SubElement(caption, vtag('langstring'))
                    langstring.text = values[idx]
                    langstring.attrib['language'] = self.langs[idx]                     
                treeworker(subtree, term)
        treeworker(self._csvdict, root)            
        return etree.tostring(root, pretty_print=True)                    