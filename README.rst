Converter from CSV file to a multilingual IMS VDEX voacabulary XML file.

VDEX is a very good standardized format for multilingual vocabularies, 
ontologies, etc. It just sucks to create its XML manually. There is poor editor 
support. But everybody has Excel, well, but almost everybody knows how to create 
tables. So let the user create a sheet with a column of keys for each term and 
for each language a column with the translated terms value. 

A flat vocabulary
-----------------

=== ======= ======== =========
key english german   italian
=== ======= ======== =========
k01 ant     Ameise   formica
k02 bee     Biene    ape   
k03 wasp    Wespe    vespa
k04 hornet  Hornisse calabrone
=== ======= ======== =========

As a csv this looks like::

    "key";"english";"german";"italian"
    "k01";"ant";"Ameise";"formica"
    "k02";"bee";"Biene";"ape"
    "k03";"wasp";"Wespe";"vespa"
    "k04";"hornet";"Hornisse";"calabrone"

After running through csv2vdex, called like so::

    csv2vdex insects 'insects,Insekten,insetto' \
             insects.csv insects.xml --languages en,de,it --startrow 1

This results it such a VDEX XML::

    <vdex xmlns="http://www.imsglobal.org/xsd/imsvdex_v1p0" orderSignificant="true">
      <vocabIdentifier>insects</vocabIdentifier>
      <vocabName>
        <langstring language="en">insects</langstring>
        <langstring language="de">Insekten</langstring>
        <langstring language="it">insetto</langstring>
      </vocabName>
      <term>
        <termIdentifier>k01</termIdentifier>
        <caption>
          <langstring language="en">ant</langstring>
          <langstring language="de">Ameise</langstring>
          <langstring language="it">formica</langstring>
        </caption>
      </term>
      <term>
        <termIdentifier>k02</termIdentifier>
        <caption>
          <langstring language="en">bee</langstring>
          <langstring language="de">Biene</langstring>
          <langstring language="it">ape</langstring>
        </caption>
      </term>
      <term>
        <termIdentifier>k03</termIdentifier>
        <caption>
          <langstring language="en">wasp</langstring>
          <langstring language="de">Wespe</langstring>
          <langstring language="it">vespa</langstring>
        </caption>
      </term>
      <term>
        <termIdentifier>k04</termIdentifier>
        <caption>
          <langstring language="en">hornet</langstring>
          <langstring language="de">Hornisse</langstring>
          <langstring language="it">calabrone</langstring>
        </caption>
      </term>
    </vdex>

A tree vocabulary
-----------------

If we want to have a tree-like vocabulary, the key is used to define the level.
Here a dot is used as delimiter.

===== ====================
key   term value
===== ====================
nwe   North-west of Europe
nwe.1 A. m. iberica
nwe.2 A. m. intermissa
nwe.3 A. m. lihzeni
nwe.4 A. m. mellifera
nwe.5 A. m. sahariensis
swe   South-west of Europe
swe.1 A. m. carnica
swe.2 A. m. cecropia
swe.3 A. m. ligustica
swe.4 A. m. macedonica
swe.5 A. m. ruttneri
swe.6 A. m. sicula
===== ====================

As a CSV it looks like::

    "key";"term value"
    "nwe";"North-west of Europe"
    "nwe.1";"A. m. iberica"
    "nwe.2";"A. m. intermissa"
    "nwe.3";"A. m. lihzeni"
    "nwe.4";"A. m. mellifera"
    "nwe.5";"A. m. sahariensis"
    "swe";"South-west of Europe"
    "swe.1";"A. m. carnica"
    "swe.2";"A. m. cecropia"
    "swe.3";"A. m. ligustica"
    "swe.4";"A. m. macedonica"
    "swe.5";"A. m. ruttneri"
    "swe.6";"A. m. sicula"

After running through csv2vdex, called like so::

    csv2vdex beeeurope 'European Honey Bees' bees.csv bees.xml -s 1
    
The result is::

    <vdex xmlns="http://www.imsglobal.org/xsd/imsvdex_v1p0" orderSignificant="true">
      <vocabIdentifier>beeeurope</vocabIdentifier>
      <vocabName>
        <langstring language="en">European Honey Bees</langstring>
      </vocabName>
      <term>
        <termIdentifier>nwe</termIdentifier>
        <caption>
          <langstring language="en">North-west of Europe</langstring>
        </caption>
        <term>
          <termIdentifier>nwe.1</termIdentifier>
          <caption>
            <langstring language="en">A. m. iberica</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>nwe.2</termIdentifier>
          <caption>
            <langstring language="en">A. m. intermissa</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>nwe.3</termIdentifier>
          <caption>
            <langstring language="en">A. m. lihzeni</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>nwe.4</termIdentifier>
          <caption>
            <langstring language="en">A. m. mellifera</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>nwe.5</termIdentifier>
          <caption>
            <langstring language="en">A. m. sahariensis</langstring>
          </caption>
        </term>
      </term>
      <term>
        <termIdentifier>swe</termIdentifier>
        <caption>
          <langstring language="en">South-west of Europe</langstring>
        </caption>
        <term>
          <termIdentifier>swe.1</termIdentifier>
          <caption>
            <langstring language="en">A. m. carnica</langstring>
          </caption>
        </term>
        <term>
       <term>
          <termIdentifier>swe.2</termIdentifier>
          <caption>
            <langstring language="en">A. m. cecropia</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>swe.3</termIdentifier>
          <caption>
            <langstring language="en">A. m. ligustica</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>swe.4</termIdentifier>
          <caption>
            <langstring language="en">A. m. macedonica</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>swe.5</termIdentifier>
          <caption>
            <langstring language="en">A. m. ruttneri</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>swe.6</termIdentifier>
          <caption>
            <langstring language="en">A. m. sicula</langstring>
          </caption>
        </term>
      </term>
    </vdex>
    
Help Text
=========

::

    usage: csv2vdex [-h] [--languages [LANGUAGES]] [--startrow [STARTROW]]
                    [--keycolumn [KEYCOLUMN]] [--startcolumn [STARTCOLUMN]]
                    [--ordered [ORDERED]] [--dialect [DIALECT]]
                    [--csvdelimiter [CSVDELIMITER]]
                    [--treedelimiter [TREEDELIMITER]]
                    id name source target
    
    Converts CSV files to VDEX XML
    
    positional arguments:
      id                    unique identifier of vocabulary
      name                  Human readable name of vocabulary. If more than one
                            language is given separate each langstring by a colon
                            and provide same order as argument --languages
      source                CSV file to read from
      target                XML target file
    
    optional arguments:
      -h, --help            show this help message and exit
      --languages [LANGUAGES], -l [LANGUAGES]
                            Comma separated list of ISO-language codes. Default:
                            en
      --startrow [STARTROW], -r [STARTROW]
                            number of row in CSV file where to begin reading,
                            starts with 0, default 0.
      --keycolumn [KEYCOLUMN], -k [KEYCOLUMN]
                            number of column with the keys of the vocabulary,
                            start with 0, default 0.
      --startcolumn [STARTCOLUMN], -s [STARTCOLUMN]
                            number of column with the first langstring of the
                            vocabulary. It assume n + number languages of columns
                            after this, starts counting with 0, default 1.
      --ordered [ORDERED], -o [ORDERED]
                            Wether vocabulary is ordered or not, Default: True
      --encoding [ENCODING], -e [ENCODING]
                            Encoding of input file. Default: utf-8
      --dialect [DIALECT]   CSV dialect, default excel.
      --csvdelimiter [CSVDELIMITER]
                            CSV delimiter of the source file, default colon.
      --treedelimiter [TREEDELIMITER]
                            Delimiter used to split the key the vocabulary into a
                            path to determine the position in the tree, default
                            dot.
  
Source Code
===========

The sources are in a GIT DVCS with its main branches at 
`github <http://github.com/bluedynamics/vdexcsv>`_.

We'd be happy to see many forks and pull-requests to make vdexcsv even better.

Contributors
============

- Jens W. Klein <jens@bluedynamics.com>

- Peter Holzer <hpeter@agitator.com>

