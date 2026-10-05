# openAIX

JSON schemas for air tasking and airspace control data in flight simulators:
Air Tasking Orders (ATO), Airspace Control Orders (ACO), control measures,
navigation data and supporting orders (SPINS, OPORD, FRAGO). The aim is a
common file format that mission planners and controller tools can exchange.

Simulator-specific data lives under `extensions.sim`. DCS is the only simulator
covered so far.

## What's here

- `schemas/`: the schemas. Orders, targeting (TST, JIPTL), loadouts (SCL),
  control measures under `schemas/measures/`, and navigation records
  (airfields, runways, procedures, holds, navaids, airways).
- `catalogues/`: lookup tables, such as which schema each doctrinal control-measure
  code maps to.
- `examples/`: sample data. Most of it is one invented ATO day for Operation
  INHERENT RESOLVE on the DCS Syria map. `examples/minimal/` and
  `examples/maximal/` hold a bare and a fully populated example for each schema.
  There are also Denver navigation records from FAA data and a few US airspace
  types.
- `tools/openaix/`: the Python package that generates all of the above.

`schemas/`, `catalogues/` and `examples/` are generated. Edit `tools/` or
`sources/` and run `task generate`.

## Usage

You need Python 3, Node.js and [Task](https://taskfile.dev).

```sh
python3 -m pip install --user jsonschema referencing rfc3339-validator PyYAML
task verify
```

`task verify` runs the tests, checks that generated files are up to date and
validates the examples.

`task viewer` starts a local browser for the schemas and examples on
http://127.0.0.1:8090.
