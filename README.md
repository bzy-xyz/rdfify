rdfify
======

Converting XML documents to RDF/N3 with minor heuristics for common use cases.

Usage
=====

    rdfify2.py -o outputfile -z schemaoutputfile -s additionalschema1 \
    -s additionalschema2 -s additionalschemaN -- inputfile

Caveats
=======

The current prototype has the following properties:

* Produces a structural RDF representation of the input XML data, with type
  annotation.
* Produces a RDFS representation of all referenced and specified schemata.
* Identifies tag IDs, and uses them to label RDF nodes.
* Identifies reference-type tags, and tries to link them to corresponding
ID'd nodes.

The current prototype has the following limitations:

* Tail text is lost.
* Nodes are created in the '#' namespace. This is not yet configurable.
