# TikTok Report Updates

`index.html` is a static report page. It loads `report.json` on every page
load, so publishing a new report only requires replacing that JSON file.

Before replacing the report, create a local backup and update atomically:

```bash
python reports/tiktok/update_report.py /path/to/new-report.json
```

The previous report is stored in:

```text
.cache/tiktok_report_backups/report-<UTC timestamp>.json
```

The separate collection cache is stored in:

```text
.cache/tiktok_report_cache.json
```

For every product traversal, update one product record at a time. Products
without `达人视频精选` must remain in `products` with:

```json
{
  "featured_section": null,
  "featured_count": null,
  "videos": [],
  "status": "checked-no-featured-section"
}
```

Use `null` for IDs or names that are not visible. Do not overwrite the report
directly from an unvalidated or partial JSON document.
