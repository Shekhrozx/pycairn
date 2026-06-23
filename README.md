# PyCairn (A simple and lightweight pipeline manifest writer tool for Python)

This is a simple and lightweight pipeline manifest writer tool for Python. It allows you to easily track the steps of your data processing pipeline, including inputs, outputs, parameters, and metrics.

## Installation
You can install PyCairn using pip:

```bash
pip install pycairn
```

## Usage

```python
from pycairn import Artifact, Cairn

cairn = Cairn(pipeline="etl", run_id="2026-06-23T01", path="2026-06-23T01.json")

# Step 1: extract
with cairn.step("extract", params={"source": "api/v2"}) as s:
    out = run_extract()  # writes data/raw.parquet
    art = Artifact.from_path("/path/to/file", type="file-type", rows=len(out))
    s.outputs.append(art)
    s.metrics["rows"] = len(out)

# Step 2: transform
prev = cairn.output_of("extract")[0].path
with cairn.step("transform", inputs=[prev]) as s:
    df = run_transform(prev)  # writes data/clean.parquet
    s.outputs.append(Artifact.from_path("data/clean.parquet", type="parquet", rows=len(df)))
    s.metrics["null_rate"] = 0.02

...
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Contributing
Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgements
- Inspired by the need for a simple and effective way to track data processing pipelines in Python.