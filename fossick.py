#!/usr/bin/env python3

"""
Fossick v1.0
"""

import argparse
import csv
import logging
import requests
import sys
from googleapiclient.discovery import build

PARSER = argparse.ArgumentParser(description='Tool to perform search engine(s) query and return HTTP status of found links')
PARSER.add_argument('--verbose', '-v', action='store_true', help='increase output verbosity')

# Default arguments

GROUP_DEFAULT = PARSER.add_argument_group('Default')
GROUP_DEFAULT.add_argument('--search-query', '-s', required=True, help='search query to be used against search engine(s)')
GROUP_DEFAULT.add_argument('--write-csv', '-w', action='store_true', required=False, help='output results to a CSV file (prints only to console if not present)')

# Google arguments

GROUP_GOOGLE = PARSER.add_argument_group('Google Search Engine')
GROUP_GOOGLE.add_argument('--google-api', '-ga', required=True, help='Google API key')
GROUP_GOOGLE.add_argument('--google-cse', '-gc', required=True, help='Google CSE ID')


ARGS = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])

if not ARGS.search_query:
    PARSER.error('--search-query must be specified')

if not ARGS.google_api or not ARGS.google_cse:
    PARSER.error('--google-api and --google-cse must be specified')

verbose_print = print if ARGS.verbose else lambda *a, **k: None
logging.basicConfig(format='%(message)s', level=logging.INFO, stream=sys.stderr)
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)


def google_search(search_term, api_key, cse_id, **kwargs):
    """ Perform Google search using search term

    Args:
        search_term ([str]): Google search term string
        api_key ([str]): Google API Key value
        cse_key ([str]): Google CSE Key value

    Returns:
        result [str]: JSON search object result
    """
    service = build('customsearch', 'v1', developerKey=api_key, cache_discovery=False)
    result = service.cse().list(q=search_term, cx=cse_id, **kwargs).execute()  # pylint: disable=no-member

    verbose_print(f'\t[d]{result}')

    return result


def extract_urls(results):
    """ Extracts URL links from the result JSON

    Args:
        results ([str]): JSON search results

    Returns:
        link_list ([list]): List of URL links parsed
    """
    link_list = []
    items = results.get('items')

    for item in items:
        link_list.append(item.get('link'))

    return link_list


def check_url_status(url, session):
    """ Requests URL link HTTP status

    Args:
        link ([str]): URL link to check HTTP status of

    Returns:
        status ([str]) : HTTP status of link checked
    """
    response = session.get(url)

    verbose_print(f'\t[d]{response.headers}')

    return response.status_code


def parse_results(search_engine, url, http_code):
    """ parse result item into dict 

    Args:
        search_engine ([str]): search engine value
        url ([str]): url value
        http_code ([str]): http code value

    Returns:
        [dict]: returns dict structure of result item
    """
    return {
        'search_engine': search_engine,
        'url': url,
        'http_code': http_code
    }


def save_output_csv(filename, search_results):
    try:
        with open(filename, mode='w') as csv_file:
            field_names = ['search_engine', 'url', 'http_code']
            writer = csv.DictWriter(csv_file, fieldnames=field_names)

            writer.writeheader()

            for item in search_results:
                writer.writerow(item)
    except OSError as e:
        logging.error(f'[ERROR] Creating CSV file - debug info: {e}')


def main():
    """ 
    Main function
    """
    logging.info(f"[i] Fossick v1.0")
    verbose_print(f"Command inputs: {ARGS}")

    # Search Google Search Engine
    google_search_results = google_search(ARGS.search_query, ARGS.google_api, ARGS.google_cse)
    google_search_urls = extract_urls(google_search_results)

    # Create requests session
    session = requests.Session()

    # Create empty list to store all results
    results = []

    if google_search_urls:
        for url in google_search_urls:
            http_code = check_url_status(url, session)
            item = parse_results('Google', url, http_code)
            results.append(item)

    # Print to console
    for item in results:
        search_engine = item.get('search_engine')
        url = item.get('url')
        http_code = item.get('http_code')
        logging.info(f'[i] Found Link : {url} \n    Status : HTTP {http_code} \n    Search Engine : {search_engine}')

    # Save to CSV file
    if ARGS.write_csv:
        filename = "fossick-results.csv"
        save_output_csv(filename, results)
        logging.info(f'[i] Successfully saved output to CSV file search-engine-results.csv')


if __name__ == "__main__":
    main()
