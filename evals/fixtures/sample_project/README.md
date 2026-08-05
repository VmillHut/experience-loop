# Sample Delivery Project

This small standard-library Python project models an asset download service. It
exists only for Experience Loop release evaluation.

Run tests with:

```bash
python -m unittest discover -s tests -v
```

Evaluation scenarios:

1. Incident: a transient failure is retried one time too few.
2. Architecture: decide whether cache policy belongs in the downloader or in a
   separate policy object without changing the public `AssetService` API.
