# Fossick

Fossick is a tool to query search engine APIs. Returns link results and the HTTP status codes for each link.

---

## Search Engine Support

The following search engines are currently supported:

* Bing
* Google

## Useage

Print the help with `python fossick.py -h`.

```
optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         increase output verbosity

Default:
  --search-query SEARCH_QUERY, -s SEARCH_QUERY
                        search query to be used against search engine(s)
  --write-csv, -w       output results to a CSV file (prints only to console if not present)

Google Search Engine:
  --google-api GOOGLE_API, -ga GOOGLE_API
                        Google API key
  --google-cse GOOGLE_CSE, -gc GOOGLE_CSE
                        Google CSE ID

Google Search Engine:
  --bing-key BING_KEY, -bk BING_KEY
                        Bing subscription key
```

### Examples

Run query against Bing and Google search engines and write results to CSV file.

`./fossick.py -s 'test query' -ga 'google-api-key' -gc 'google-cse-id' -bk 'bing-sub-key' -w`

Run query against Bing and Google search engines and download files locally.

`./fossick.py -s 'test query' -ga 'google-api-key' -gc 'google-cse-id' -bk 'bing-sub-key' -d`



