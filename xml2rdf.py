# prototype rdfification of arbitrary XML without XSD information.

# TODO:
# * Allow arbitrary specification of "id" markers.
# * Handle references correctly.
# * Allow arbitrary specification of "ref" markers.
# * Allow the destination namespace for nodes to be specified.

# Questions to answer:
# * Can the *absence* of information ever be significant?

import lxml
import lxml.etree
import rdflib
import sys
import os
import re
import argparse

ns_rdfify = u'http://dig.csail.mit.edu/2014/rdfify/schema#'

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

def constructXMLName(namespace, element):
    return '{' + namespace + '}' + element

def constructURIRefFromXMLName(n):
    k = n[1:].split('}')
    return constructURIRef(k[0], k[1])

def lookupTagType(tag, schema_data):
    return schema_data.elementMap.get(tag, tag)

def lookupAttributeType(tag, schema_data):
    return schema_data.attributeMap.get(tag, "{http://www.w3.org/2001/XMLSchema}string")

def processNode(tag, graph, parentNode, schema_data):
    """ Converts a XML tag and children to RDF graph nodes.
    """

    # only process actual tags, not comments
    if isinstance(tag.tag, basestring):

        # split the tag into namespace and local name
        tag_qn = lxml.etree.QName(tag)

        # collapse whitespace in tag text
        if tag.text:
            tag_text = re.sub("\s+"," ",tag.text)
        else:
            tag_text = None


        # build the RDF nodes and triples implied by the tag

        # 0: tag is the root entity -> (BNode rdf:type URIRef)
        # 1: tag has children / attributes -> (parent URIRef BNode)
        # 1.1: the 'ref' markers doesn't count as an attribute if it's the only one
        # 1a: tag also has text -> (BNode <rdfify:hasText> Literal)
        # 2: tag has no children and some text -> (parent URIRef Literal)
        # 3: tag has no children and no text -> (parent URIRef [])

        node = None

        # tag is the root entity
        if parentNode == None:
            node = rdflib.BNode().skolemize()
            pred = rdflib.namespace.RDF.type
            print tag.tag
            obj = constructURIRefFromXMLName(lookupTagType(tag.tag, schema_data))
            graph.add((node, pred, obj))

        # tag has children / attributes
        elif len(tag.getchildren()) or len(tag.keys()):
            node = rdflib.BNode()
            ignore_text = False

            # experimental support for adding labels to 'significant' nodes
            # based on the simple heuristic of 'does this node have an id attribute'
            if len(tag.keys()):
                for k, v in sorted(tag.items()):
                    k_qn = lxml.etree.QName(k)
                    #if k_qn.localname == "id":
                    if lookupAttributeType(k, schema_data) in ("{http://www.w3.org/2001/XMLSchema}ID",):
                        node = rdflib.URIRef(u"#{0}".format(v))
                        break
                    # experimental support for reference-like tags
                    # invoked only if the reference tag has no other content or attributes
                    #if k_qn.localname == "ref" and len(tag.keys()) == 1 and len(tag.getchildren()) == 0:
                    if lookupAttributeType(k, schema_data) in ("{http://www.w3.org/2001/XMLSchema}IDREF", "{http://www.w3.org/2001/XMLSchema}NCName") and len(tag.keys()) == 1 and len(tag.getchildren()) == 0:
                        node = rdflib.URIRef(u"#{0}".format(v))
                        del tag.attrib[k]
                        ignore_text = True
                        break

            # tags with both children and text get the text in a separate triple
            if not ignore_text and tag_text and tag_text != " ":
                pred = rdflib.URIRef(ns_rdfify + 'hasText')
                obj = rdflib.Literal(tag_text)
                graph.add((node, pred, obj))
            pred = constructURIRef(tag_qn.namespace, tag_qn.localname)
            graph.add((parentNode, pred, node))

            # type annotation
            graph.add((node, rdflib.namespace.RDF.type, constructURIRefFromXMLName(lookupTagType(tag.tag, schema_data))))

        # tag has no children and no attributes (i.e. pure literal value)
        else:
            if tag_text:
                # TODO add type annotation
                node = rdflib.Literal(tag_text)
            else:
                node = rdflib.BNode()
            pred = constructURIRef(tag_qn.namespace, tag_qn.localname)
            graph.add((parentNode, pred, node))

        # tags with attributes get their own per-attribute triples
        if len(tag.keys()):
            for k, v in sorted(tag.items()):
                k_qn = lxml.etree.QName(k)
                pred = constructURIRef(k_qn.namespace, k_qn.localname)
                obj = rdflib.Literal(v)
                graph.add((node, pred, obj))

        # recursively process any children
        for child in tag.getchildren():
            processNode(child, graph, node, schema_data)

def parseXMLDocument(xml_root, graph, schema_data):
    processNode(xml_root, graph, None, schema_data)

    for k, v in xml_root.nsmap.iteritems():
        graph.bind(k, normalizeNamespace(v))
