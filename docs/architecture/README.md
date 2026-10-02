# Architecture

The engineering baseline is a modular monolith: `api → application → domain`, while
`infrastructure` implements external ports. The web frontend and offline ML workspace
remain separate from the runtime backend. The product source is
[`docs/product/CONCEPT.md`](../product/CONCEPT.md): a creative task produces a result
grounded in curated cultural sources. PostgreSQL governs exact source revisions
and publication state, private storage holds original files, and Qdrant indexes versioned
embeddings. Retrieval rechecks current PostgreSQL authority after vector candidate
search. The first slice indexes text; [ADR 0006](../decisions/0006-vector-retrieval-and-media.md)
defines the extension for visual and audio representations.
