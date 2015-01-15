import lxml
import lxml.etree
import rdflib
import sys
import os
import re
import argparse
import tempfile
import itertools

ns_rdfify = u'http://dig.csail.mit.edu/2014/rdfify/schema#'

from builtin_types import builtInDatatypeNames

import xml2rdf
import xsd2rdfs

## stuff goes here

class SchemaData:
    def __init__(self):
        self.simpleTypeMap = {}
        self.complexTypeMap = {}
        self.elementMap = {}
        self.attributeMap = {}
        self.schemataVisited = []

def nsExpand(name, nsMap):
    """Expands the given `name` into {namespace}shortName form using the given nsMap.
       Undefined for names with multiple : characters."""
    splitName = name.split(':')
    if len(splitName) < 2:
        return name
    if len(splitName) > 2:
        raise NotImplementedError('trying to nsExpand name {0} with multiple :'.format(name))
    if splitName[0] not in nsMap:
        return name
    return "{" + nsMap[splitName[0]] + "}" + splitName[1]

def namespaceLocationToPath(ns, loc):
    #if "://" in loc:
    #    return loc
    #else:
    #    return ns + ("/" if ns[-1] != "/" else "") + loc
    return loc

def parseSchemaLocations(xml_root):
    ret = []

    # load any schemata referenced by the root node
    schemata = xml_root.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation")
    if schemata:
        schemata_split = schemata.split(" ")

        # process the schemata entries by pairs (first element is namespace, second element is relative path)
        i = iter(schemata_split)
        real_schemata = itertools.izip(i,i)

        ret = []

        for schema_pair in real_schemata:
            ret.append(namespaceLocationToPath(schema_pair[0], schema_pair[1]))

    # load any schemata referenced by imports
    for child in xml_root.getchildren():
        if lxml.etree.QName(child).text == "{http://www.w3.org/2001/XMLSchema}import":
            ret.append(namespaceLocationToPath(child.get("namespace"), child.get("schemaLocation")))

    return ret

def extractRDFGraphWithSchema(xml_root, extra_schemata):
    g = rdflib.Graph()
    s = rdflib.Graph()
    sdata = SchemaData()

    # load all referenced schemata and process them
    print "processing schemata"
    for schema in parseSchemaLocations(xml_root):
        xsd2rdfs.parseXMLSchema(schema, s, sdata)
    for schema in extra_schemata:
        xsd2rdfs.parseXMLSchema(schema, s, sdata)


    print "processing XML"
    xml2rdf.parseXMLDocument(xml_root, g, sdata)

    return (g, s)

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('xmlfile')
    argparser.add_argument('-t','--output-type', default='n3')
    argparser.add_argument('-o','--outfile', default=None)
    argparser.add_argument('-z','--schema-outfile', default=None)
    argparser.add_argument('-s','--include-schema', action='append')

    args = argparser.parse_args()

    outfile = args.outfile
    schema_outfile = args.schema_outfile
    output_type = args.output_type

    # Extract the root element
    t = lxml.etree.parse(args.xmlfile)
    r = t.getroot()

    # Extract a RDF graph from the given root element.
    # This step does everything else.

    g, s = extractRDFGraphWithSchema(r, args.include_schema)

    print "exporting"

    # If schema-outfile is unspecified, merge the two graphs.

    if not schema_outfile:

        # Save both graphs to a tmpdir
        stmp = tempfile.NamedTemporaryFile()
        gtmp = tempfile.NamedTemporaryFile(delete=False)


        stmp.write(s.serialize(format='n3'))
        gtmp.write(g.serialize(format='n3'))

        stmp.flush()
        gtmp.flush()

        # Then merge the two graphs
        g = rdflib.Graph()
        g.parse(stmp.name, format='n3')
        g.parse(gtmp.name, format='n3')

    # Write the graph to the given file (or stdout)
    if outfile:
      with open(outfile, 'w') as f:
        f.write(g.serialize(format=output_type))
    else:
      print g.serialize(format=output_type)

    # Write the schema to the given file (if applicable)
    if schema_outfile:
      with open(schema_outfile, 'w') as f:
        f.write(s.serialize(format=output_type))

if __name__ == "__main__":
    main()
