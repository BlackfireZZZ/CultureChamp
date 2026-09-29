# Architecture

The engineering baseline is a modular monolith: `api → application → domain`, while
`infrastructure` implements external ports. The web frontend and offline ML workspace
remain separate from the runtime backend. The product source is
[`docs/product/CONCEPT.md`](../product/CONCEPT.md): a creative task produces a result
grounded in curated cultural sources. Concrete bounded contexts, data contracts and
generation safeguards will be defined in subsequent decisions and implementation
plans; the concept alone does not specify them.
