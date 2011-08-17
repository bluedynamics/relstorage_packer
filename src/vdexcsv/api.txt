
    >>> from vdexcsv import api 
    
Find the field names::

    >>> c2v = api.CSV2VDEX('foo', 'Foo', 'foo.csv', 'foo.xml')
    >>> c2v._fields
    ['key', 'en']

    >>> c2v = api.CSV2VDEX('foo', 'FooEn,FooDe', 'foo.csv', 'foo.xml', 
    ...                    langs=['en','de'])
    >>> c2v.names
    OrderedDict([('en', 'FooEn'), ('de', 'FooDe')])
    
    >>> c2v._fields
    ['key', 'en', 'de']

    >>> c2v = api.CSV2VDEX('foo', 'Foo', 'foo.csv', 'foo.xml', colkey=3)
    >>> c2v._fields
    ['__genkey-0', 'en', '__genkey-2', 'key']

    >>> c2v = api.CSV2VDEX('foo', 'Foo', 'foo.csv', 'foo.xml', colkey=1)
    >>> c2v._fields
    Traceback (most recent call last):
    ...
    ValueError: key column is in same range as value columns
    
Get the CSV, first flat::   

    >>> import os
    >>> testdatadir =  os.path.join(os.path.dirname(api.__file__), 'testdata')
    >>> infilename = os.path.join(testdatadir, 'test1.csv')
    >>> c2v = api.CSV2VDEX('test', 'Test', infilename, 'test1.xml', startrow=1, 
    ...                    langs=['en', 'de'])    
    >>> c2v._csvdict
    OrderedDict([('100', (OrderedDict(), ['hundered', 'hundert'], '100')), 
    ('1000', (OrderedDict(), ['thousand', 'tausend'], '1000')), ('10000', 
    (OrderedDict(), ['ten thousand', 'zehntausend'], '10000'))])
    
and as tree::

    >>> infilename = os.path.join(testdatadir, 'test2.csv')
    >>> c2v = api.CSV2VDEX('test', 'TestEn,TestDe', infilename, 
    ...                    'test1.xml', startrow=1, langs=['en', 'de'])
    >>> c2v._csvdict
    OrderedDict([('100', (OrderedDict([('1', (OrderedDict(), ['one', 'eins'], 
    '100.1')), ('2', (OrderedDict(), ['two', 'zwei'], '100.2'))]), ['hundered', 
    'hundert'], '100')), ('1000', (OrderedDict([('a', (OrderedDict(), ['A', 
    'A'], '1000.a')), ('b', (OrderedDict(), ['B', 'B'], '1000.b'))]), 
    ['thousand', 'tausend'], '1000')), ('10000', (OrderedDict([('X', 
    (OrderedDict([('YZ', (OrderedDict(), ['YZ', 'YZ'], '10000.X.YZ')), ('123', 
    (OrderedDict(), ['one two three', 'eins zwei drei'], '10000.X.123'))]), 
    ['ex', 'ix'], '10000.X')), ('Y', (OrderedDict(), ['epsilon', 'ypsilon'], 
    '10000.Y'))]), ['ten thousand', 'zehntausend'], '10000'))])
    
    
Get the XML::

    >>> print c2v._xml 
    <vdex xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.imsglobal.org/xsd/imsvdex_v1p0" xsi:schemaLocation="http://www.imsglobal.org/imsvdex_v1p0 imsvdex_v1p0.xsd" profileType="lax" orderSignificant="true">
      <vocabIdentifier>test</vocabIdentifier>
      <vocabName>
        <langstring language="en">TestEn</langstring>
        <langstring language="de">TestDe</langstring>
      </vocabName>
      <term>
        <termIdentifier>100</termIdentifier>
        <caption>
          <langstring language="en">hundered</langstring>
          <langstring language="de">hundert</langstring>
        </caption>
        <term>
          <termIdentifier>100.1</termIdentifier>
          <caption>
            <langstring language="en">one</langstring>
            <langstring language="de">eins</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>100.2</termIdentifier>
          <caption>
            <langstring language="en">two</langstring>
            <langstring language="de">zwei</langstring>
          </caption>
        </term>
      </term>
      <term>
        <termIdentifier>1000</termIdentifier>
        <caption>
          <langstring language="en">thousand</langstring>
          <langstring language="de">tausend</langstring>
        </caption>
        <term>
          <termIdentifier>1000.a</termIdentifier>
          <caption>
            <langstring language="en">A</langstring>
            <langstring language="de">A</langstring>
          </caption>
        </term>
        <term>
          <termIdentifier>1000.b</termIdentifier>
          <caption>
            <langstring language="en">B</langstring>
            <langstring language="de">B</langstring>
          </caption>
        </term>
      </term>
      <term>
        <termIdentifier>10000</termIdentifier>
        <caption>
          <langstring language="en">ten thousand</langstring>
          <langstring language="de">zehntausend</langstring>
        </caption>
        <term>
          <termIdentifier>10000.X</termIdentifier>
          <caption>
            <langstring language="en">ex</langstring>
            <langstring language="de">ix</langstring>
          </caption>
          <term>
            <termIdentifier>10000.X.YZ</termIdentifier>
            <caption>
              <langstring language="en">YZ</langstring>
              <langstring language="de">YZ</langstring>
            </caption>
          </term>
          <term>
            <termIdentifier>10000.X.123</termIdentifier>
            <caption>
              <langstring language="en">one two three</langstring>
              <langstring language="de">eins zwei drei</langstring>
            </caption>
          </term>
        </term>
        <term>
          <termIdentifier>10000.Y</termIdentifier>
          <caption>
            <langstring language="en">epsilon</langstring>
            <langstring language="de">ypsilon</langstring>
          </caption>
        </term>
      </term>
    </vdex>
    