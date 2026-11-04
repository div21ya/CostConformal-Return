# CostConformal-Return — live demo

Run this folder with any static web server from the project root:

```bash
python3 -m http.server 8000
```

Then open [http://localhost:8000/live_demo/](http://localhost:8000/live_demo/).

The demo is intentionally dependency-free. It uses the persisted CSV results in
`outputs/tables/` as its source and links to the rendered Quarto reports in
`files/` for the complete stage-by-stage evidence.
