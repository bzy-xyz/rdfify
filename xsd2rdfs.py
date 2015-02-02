import lxml
import lxml.etree
import rdflib
import rdflib.namespace
import sys
import os
import re
import argparse
import urlparse

builtInDatatypeNames = set(['{http://www.w3.org/2001/XMLSchema}' + n for n in [
    'string',
    'duration',
    'dateTime',
    'time',
    'date',
    'gYearMonth',
    'gYear',
    'gMonthDay',
    'gDay',
    'gMonth',
    'boolean',
    'base64Binary',
    'hexBinary',
    'float',
    'decimal',
    'double',
    'anyURI',
    'QName',
    'NOTATION',
    'normalizedString',
    'token',
    'language',
    'Name',
    'NMTOKEN',
    'NCName',
    'NMTOKENS',
    'ID',
    'IDREF',
    'ENTITY',
    'IDREFS',
    'ENTITIES',
    'integer',
    'nonPositiveInteger',
    'long',
    'nonNegativeInteger',
    'negativeInteger',
    'int',
    'unsignedLong',
    'positiveInteger',
    'unsignedInt',
    'unsignedShort',
    'unsignedByte'
]])

class ComplexTypeDescriptor:
    def __init__(self, name):
        self.name = name
        self.parentName = None
        self.elems = []
        self.attrs = []

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

def processRawNode(tag, data):
    #print '{0}{1} {2} "{3}"'.format(' '*level, tag.tag, tag.attrib, tag.text.strip() if tag.text else '')
    for child in tag.getchildren():
        if isinstance(child.tag, basestring):
            tag_qn = lxml.etree.QName(child)
            if tag_qn.localname in data:
                data[tag_qn.localname].append(child)

def processSimpleType(tag, typeMap, nsMap, targetNS = "#"):
    name = "{{{0}}}{1}".format(targetNS, tag.get('name'))
    for child in tag.getchildren():
        # ignore annotations for now
        if child.tag == "{http://www.w3.org/2001/XMLSchema}annotation":
            continue

        # TODO what do we do about lists?
        if child.tag == "{http://www.w3.org/2001/XMLSchema}list":
            # treat them as strings for now
            typeMap[child.tag] = "{http://www.w3.org/2001/XMLSchema}string"
            continue

        # tag has a base
        n = child.get('base')
        if n:
            typeMap[name] = nsExpand(n, nsMap)
            continue

        #raise NotImplementedError('unhandled tag {0} in simpleType {1}'.format(child.tag, name))

def processComplexType(tag, complexTypeMap, nsMap, targetNS = "#"):
    name = "{{{0}}}{1}".format(targetNS, tag.get('name'))
    tagDescriptor = ComplexTypeDescriptor(name)

    def processChild(child, name, tagDescriptor, nsMap, targetNS):
        # ignore annotations for now
        if child.tag == "{http://www.w3.org/2001/XMLSchema}annotation":
            return

        # complexContent and simpleContent are handled more-or-less the same
        if child.tag == "{http://www.w3.org/2001/XMLSchema}complexContent" \
        or child.tag == "{http://www.w3.org/2001/XMLSchema}simpleContent":
            # we extract the information we need from inside the content tag
            # including the base

            for e in child.iter():
                if e == child:
                    continue

                n = e.get('base')
                if n:
                    tagDescriptor.parentName = nsExpand(n, nsMap)
                    return

                else:
                    pass
                    #print "unhandled tag {0} in complexType {1}".format(e.tag, name)



        #raise NotImplementedError('unhandled tag {0} in complexType {1}'.format(child.tag, name))

    for child in tag.getchildren():
        processChild(child, name, tagDescriptor, nsMap, targetNS)

    #complexTypeMap[name] = tagDescriptor.parentName
    complexTypeMap[name] = tagDescriptor.parentName


def processAttribute(tag, attributeMap, nsMap, targetNS = "#"):
    name = "{{{0}}}{1}".format(targetNS, tag.get('name'))
    attrType = tag.get('type')
    for child in tag.getchildren():
        # ignore annotations for now
        if child.tag == "{http://www.w3.org/2001/XMLSchema}annotation":
            continue
        #raise NotImplementedError('unhandled tag {0} in attribute {1}'.format(child.tag, name))
    if attrType:
        attributeMap[name] = nsExpand(attrType, nsMap)

def processAttributeGroup(tag, attributeGroupMap, nsMap, targetNS = "#"):
    name = "{{{0}}}{1}".format(targetNS, tag.get('name'))
    for child in tag.getchildren():
        # ignore annotations for now
        if child.tag == "{http://www.w3.org/2001/XMLSchema}annotation":
            continue
        #raise NotImplementedError('unhandled tag {0} in attributeGroup {1}'.format(child.tag, name))

def processElement(tag, elementMap, nsMap, targetNS = "#"):
    name = "{{{0}}}{1}".format(targetNS, tag.get('name'))
    # TODO: Some elements define anonymous simpleType or complexType types;
    # it's not clear how we want to handle these.
    elemType = tag.get('type')
    for child in tag.getchildren():
        # ignore annotations for now
        #print child
        if child.tag == "{http://www.w3.org/2001/XMLSchema}annotation":
            continue
        #raise NotImplementedError('unhandled tag {0} in element {1}'.format(child.tag, name))
    if elemType:
        elementMap[name] = nsExpand(elemType, nsMap)


def extractMappingsFromSchema(schema_root_node, schema_data):

    #t = lxml.etree.parse(schema_loc)
    r = schema_root_node

    nsMap = dict(r.nsmap)
    targetNS = r.get('targetNamespace')

    z = {
        'complexType': [],
        'simpleType': [],
        'element': [],
        'attribute': [],
        'attributeGroup': [],
    }

    processRawNode(r, z)

    simpleTypeMap = {}
    complexTypeMap = {}
    attributeMap = {}
    elementMap = {}

    for t in z['simpleType']:
        processSimpleType(t, simpleTypeMap, nsMap, targetNS)

    for t in z['attribute']:
        processAttribute(t, attributeMap, nsMap, targetNS)

    for t in z['complexType']:
        processComplexType(t, complexTypeMap, nsMap, targetNS)

    for t in z['element']:
        processElement(t, elementMap, nsMap, targetNS)

    schema_data.simpleTypeMap.update(simpleTypeMap)
    schema_data.complexTypeMap.update(complexTypeMap)
    schema_data.attributeMap.update(attributeMap)
    schema_data.elementMap.update(elementMap)

def reduceSimpleTypeMap(typeMap):
    """Reduces type map entries to XML built-in datatypes where possible,
       or to xsd:string where not.

       Done in place.

       Expects that all linked schemata have already been recursively explored;
       otherwise it may well turn everything into xsd:string."""

    for k in typeMap:
        # trace upwards through the type map
        cur = typeMap[k]
        while cur in typeMap:
            cur = typeMap[cur]

        if cur not in builtInDatatypeNames:
            cur = '{http://www.w3.org/2001/XMLSchema}string'

        typeMap[k] = cur

def getPathRelativeToReferencePath(path, ref_path):
    return urlparse.urljoin(ref_path, path)

def normalizeNamespace(namespace):
    if namespace[-1] != '#' and namespace[-1] != '/' and namespace != "http://www.w3.org/XML/1998/namespace":
        return namespace + '#'
    else:
        return namespace

def constructURIRef(namespace, element):
    if namespace[-1] != '#' and namespace[-1] != '/' and namespace != "http://www.w3.org/XML/1998/namespace":
        return rdflib.URIRef(u"{0}#{1}".format(namespace, element))
    else:
        return rdflib.URIRef(u"{0}{1}".format(namespace, element))

def parseXMLSchemaRecursive(schema_loc, schema_graph, schema_data):

    #print "parsing schema at", schema_loc

    t = lxml.etree.parse(schema_loc)
    r = t.getroot()

    for k, v in r.nsmap.iteritems():
        schema_graph.bind(k, normalizeNamespace(v))

    extractMappingsFromSchema(r, schema_data)

    schema_data.schemataVisited.append(schema_loc)

    for c in r.getchildren():
        if c.tag == "{http://www.w3.org/2001/XMLSchema}import":
            newloc = c.get('schemaLocation')
            newloc_uri = getPathRelativeToReferencePath(newloc, schema_loc)
            if newloc_uri not in schema_data.schemataVisited:
                parseXMLSchemaRecursive(newloc_uri, schema_graph, schema_data)

def decomposeLongTagName(tn):
    """Convert {foo}bar to (foo, bar)."""
    # quick and dirty
    return tn[1:].split('}')

def parseXMLSchema(schema_loc, schema_graph, schema_data):

    parseXMLSchemaRecursive(schema_loc, schema_graph, schema_data)

    #print "reducing type map"

    reduceSimpleTypeMap(schema_data.simpleTypeMap)


    #print "building RDFS"
    # build RDFS graph triples
    # for complex types
    for k, v in schema_data.complexTypeMap.iteritems():
        k_dec = decomposeLongTagName(k)
        n = constructURIRef(k_dec[0], k_dec[1])

        # k-node a rdfs:Class;
        schema_graph.add((n, rdflib.namespace.RDF.type, rdflib.namespace.RDFS.Class))

        if v:
            v_dec = decomposeLongTagName(v)
            nbasetype = constructURIRef(v_dec[0], v_dec[1])
            #   subClassOf v-node
            schema_graph.add((n, rdflib.namespace.RDFS.subClassOf, nbasetype))

    # for element types
    for k, v in schema_data.elementMap.iteritems():
        k_dec = decomposeLongTagName(k)

        n = constructURIRef(k_dec[0], k_dec[1])

        # k-node a rdfs:Property;
        schema_graph.add((n, rdflib.namespace.RDF.type, rdflib.namespace.RDF.Property))

        if v in schema_data.simpleTypeMap:
            vreal = schema_data.simpleTypeMap[v]
        else:
            vreal = v

        if vreal:
            v_dec = decomposeLongTagName(vreal)

            nbasetype = constructURIRef(v_dec[0], v_dec[1])

            #   rdfs:range v-node;
            schema_graph.add((n, rdflib.namespace.RDFS.range, nbasetype))

    # for attribute types
    for k, v in schema_data.attributeMap.iteritems():
        k_dec = decomposeLongTagName(k)

        n = constructURIRef(k_dec[0], k_dec[1])
        # k-node a rdfs:Property;
        schema_graph.add((n, rdflib.namespace.RDF.type, rdflib.namespace.RDF.Property))

        if v in schema_data.simpleTypeMap:
            vreal = schema_data.simpleTypeMap[v]
        else:
            vreal = v

        if vreal:
            v_dec = decomposeLongTagName(vreal)

            nbasetype = constructURIRef(v_dec[0], v_dec[1])

            #   rdfs:range v-node;
            schema_graph.add((n, rdflib.namespace.RDFS.range, nbasetype))
