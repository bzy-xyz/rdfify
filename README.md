rdfify
======

Converting XML documents to RDF/N3 with minor heuristics for common use cases.

Usage
=====

    rdfify.py input-file > output-file

Caveats
=======

The current prototype has the following properties:
 
* Produces a structural RDF representation of the input XML data.
* Identifies tag IDs, and uses them to label RDF nodes.
* Identifies reference-type tags, and tries to link them to corresponding
ID'd nodes.

The current prototype has the following limitations:

* Type information is not preserved; the nodes have no rdf:type.
* Reference type tags only work if they have exactly one attribute and no
text content.
* Tail text is lost.
* ID and reference attributes are determined with a bad heuristic that is
not user configurable.
* Nodes are created in the '#' namespace. This is not yet configurable.


