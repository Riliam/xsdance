import dill as pickle
from lxml import html, etree
from generator import Generator

from utils import tree

g = Generator()
schema = g.run('IRS/Federal/2015v3.0/IndividualIncomeTax/Ind1040/IRS1040/IRS1040.xsd')

el = schema[0]
el.parent = None

pickled = pickle.dumps(el)
unpickled = pickle.loads(pickled)

parsed = html.fragment_fromstring(unpickled.render_html())
stringed = etree.tostring(parsed).decode('utf-8')
with open('index.html', 'w') as f:
    f.write(stringed)
