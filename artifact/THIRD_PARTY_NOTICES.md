# Third-party notices

- The paper bundle includes ACL style and bibliography files supplied by the Overleaf project; their upstream terms continue to apply.
- The controlled platform is composed of seven separately versioned Git submodules. URLs and commits are in `platform/submodules.lock.json`; consult each submodule for its license and notices.
- Hugging Face hosts the external datasets. Dataset licenses are summarized in `DATA_LICENSE.md` and fixed per revision in `data/datasets.lock.json`.
- The Reddit source is the Pushshift Reddit Dataset, DOI `10.5281/zenodo.3608135`, licensed CC BY 4.0 according to the locked rebuttal source. No Reddit text is redistributed in the baseline result JSON.
- Optional baseline robustness code is pinned to `strangeloopcanon/moltbook_vs_reddit@30b9bae05635f73e08dde4231367d7f527e9f596` and is not vendored here.
