# PyCairn: A simple and lightweight pipeline manifest writer tool

This is a simple and lightweight pipeline manifest writer tool. It allows you to easily track the steps of your data processing pipeline, including inputs, outputs, parameters, and metrics.

## Installation
You can install PyCairn using pip:

```bash
pip install pycairn
```

## Usage

```python
from pycairn import Artifact, Cairn

cairn = Cairn(pipeline="data-pipeline", run_id="2026-06-23T01", path="manifest.json")

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

### Results
After running the above code, a JSON file will be created at `2026-06-23T01.json` containing the manifest of the pipeline run, including all steps, inputs, outputs, parameters, and metrics.

```json
{
  "run_id": "2026-06-23T01",
  "pipeline": "data-pipeline",
  "created_at": "2026-06-23T08:35:17.962968+00:00",
  "status": "success",
  "steps": [
    {
      "name": "extract",
      "status": "success",
      "started_at": "2026-06-23T08:35:17.963163+00:00",
      "ended_at": "2026-06-23T08:35:17.980969+00:00",
      "duration_s": 0.017497,
      "inputs": [],
      "outputs": [
        {
          "path": "/path/to/data/extracted.parquet",
          "type": "parquet",
          "bytes": 18984144,
          "sha256": "433e58d2da040dd5c876afdbed980506bfe7dc0f3bb89a9e70296d63f4bb5592",
          "meta": {
            "rows": 100
          }
        }
      ],
      "metrics": {
        "rows": 100
      },
      "params": {
        "source": "api/v2"
      },
      "error": null
    },
    {
      "name": "transform",
      "status": "success",
      "started_at": "2026-06-23T08:35:17.982632+00:00",
      "ended_at": "2026-06-23T08:35:17.982878+00:00",
      "duration_s": 0.000128,
      "inputs": [
        "data/extracted.parquet"
      ],
      "outputs": [
        {
          "path": "data/clean.parquet",
          "type": "parquet",
          "bytes": null,
          "sha256": null,
          "meta": {
            "rows": 100
          }
        }
      ],
      "metrics": {
        "null_rate": 0.02
      },
      "params": {},
      "error": null
    },
    ...
  ]
}
```


## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details

## Contributing
Contributions are welcome! Please feel free to submit issues or pull requests.

## Acknowledgements
- Inspired by the need for a simple and effective way to track data processing pipelines in Python.