    >>> from vdexcsv.script import parser

    >>> parser.print_help()
    usage: test [-h] [--languages [LANGUAGES]] [--startrow [STARTROW]]
                [--keycolumn [KEYCOLUMN]] [--startcolumn [STARTCOLUMN]]
                [--ordered [ORDERED]] [--dialect [DIALECT]]
                [--csvdelimiter [CSVDELIMITER]] [--treedelimiter [TREEDELIMITER]]
                id name source target
    <BLANKLINE>
    Converts CSV files to VDEX XML
    <BLANKLINE>
    positional arguments:
      id                    unique identifier of vocabulary
      name                  Human readable name of vocabulary. If more than one
                            language is given separate each langstring by a colon
                            and provide same order as argument --languages
      source                CSV file to read from
      target                XML target file
    <BLANKLINE>
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
      --dialect [DIALECT]   CSV dialect, default excel.
      --csvdelimiter [CSVDELIMITER]
                            CSV delimiter of the source file, default colon.
      --treedelimiter [TREEDELIMITER]
                            Delimiter used to split the key the vocabulary into a
                            path to determine the position in the tree, default
                            dot.
