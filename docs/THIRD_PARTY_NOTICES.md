# Third-party licensing and media notice

Original project source: MIT (see root LICENSE). Dependencies,
pretrained weights, codecs and sample images retain **their own** licenses and
distribution terms; MIT licensing of this repository does not relicense them.

The Python requirements currently include FastAPI, Uvicorn, Pillow, NumPy and
OpenCV; optional neural functions can use ONNX Runtime, contrib OpenCV and
third-party pretrained models. FFmpeg and H.264/AAC availability depends on
the machine and distribution. Verify all direct/transitive package licenses
and codec patent obligations before redistribution.

Downloaded `FSRCNN_x2.pb` and `ESPCN_x2.pb` test weights are not bundled in
the repository. Their upstream provenance and checksums belong in
`backend/models/pretrained.json`. Recheck rights before embedding any weights
or sample media in a downloadable installer.

Lumqenix Community licensing does not grant rights to third-party names,
trademarks or commercial Pro algorithms and assets.
