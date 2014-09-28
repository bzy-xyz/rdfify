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


def processNode(tag, graph, parentNode):
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
            obj = rdflib.URIRef(u"{0}#{1}".format(tag_qn.namespace, tag_qn.localname))
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
                    if k_qn.localname == "id":
                        node = rdflib.URIRef(u"#{0}".format(v))
                        break
                    # experimental support for reference-like tags
                    # invoked only if the reference tag has no other content or attributes
                    if k_qn.localname == "ref" and len(tag.keys()) == 1 and len(tag.getchildren()) == 0:
                        node = rdflib.URIRef(u"#{0}".format(v))
                        del tag.attrib[k]
                        ignore_text = True
                        break

            # tags with both children and text get the text in a separate triple
            if not ignore_text and tag_text and tag_text != " ":
                pred = rdflib.URIRef(ns_rdfify + 'hasText')
                obj = rdflib.Literal(tag_text)
                graph.add((node, pred, obj))
            pred = rdflib.URIRef(u"{0}#{1}".format(tag_qn.namespace, tag_qn.localname))
            graph.add((parentNode, pred, node))

        # tag has no children and no attributes (i.e. pure literal value)
        else:
            if tag_text and tag_text != " ":
                node = rdflib.Literal(tag_text)
            else:
                node = rdflib.BNode()
            pred = rdflib.URIRef(u"{0}#{1}".format(tag_qn.namespace, tag_qn.localname))
            graph.add((parentNode, pred, node))

        # tags with attributes get their own per-attribute triples
        if len(tag.keys()):
            for k, v in sorted(tag.items()):
                k_qn = lxml.etree.QName(k)
                pred = rdflib.URIRef(u"{0}#{1}".format(k_qn.namespace, k_qn.localname))
                obj = rdflib.Literal(v)
                graph.add((node, pred, obj))

        # recursively process any children
        for child in tag.getchildren():
            processNode(child, graph, node)

def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('xmlfile')
    argparser.add_argument('-t','--output-type', default='n3')
    argparser.add_argument('-o','--outfile', default=None)

    args = argparser.parse_args()

    xmlfile = args.xmlfile
    output_type = args.output_type
    outfile = args.outfile

    t = lxml.etree.parse(xmlfile)
    r = t.getroot()
    g = rdflib.Graph()

    processNode(r, g, None)

    for k, v in r.nsmap.iteritems():
        g.bind(k, v+'#')

    if outfile:
      with open(outfile, 'w') as f:
        f.write(g.serialize(format=output_type))
    else:
      print g.serialize(format=output_type)


if __name__ == "__main__":
    main()
