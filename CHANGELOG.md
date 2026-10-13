### PR #TBD - 2026-10-13
- Nemoparse markdown output now separates pages with `# <PAGE N>` headers; bbox JSON is a valid array grouped by page (`{"page", "content"}`).
- Fix `NameError` in `NemoparseOutput.get_output_as_json(with_bbox_data=False)`.

### PR #TBD - 2026-05-07
- Implement recursive directory crawling for input files.
- Add --file_extensions CLI argument for custom file filtering.
- Refactor file gathering logic into a dedicated utils module.
