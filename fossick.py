#!/usr/bin/env python3

"""
Fossick v1.0
"""

import aiohttp
import aiofiles
import argparse
import asyncio
import csv
import logging
import os
import requests
import sys
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

PARSER = argparse.ArgumentParser(description='Tool to perform search engine(s) query and return HTTP status of found links')
PARSER.add_argument('--verbose', '-v', action='store_true', help='increase output verbosity')

# Default arguments
GROUP_DEFAULT = PARSER.add_argument_group('Default')
GROUP_DEFAULT.add_argument('--download', '-d', action='store_true', required=False, help='download the link contents locally')
GROUP_DEFAULT.add_argument('--search-query', '-s', required=True, help='search query to be used')
GROUP_DEFAULT.add_argument('--write-csv', '-w', action='store_true', required=False, help='output results to a CSV file')

# Google arguments
GROUP_GOOGLE = PARSER.add_argument_group('Google Search Engine')
GROUP_GOOGLE.add_argument('--google-api', '-ga', required=False, help='Google API key')
GROUP_GOOGLE.add_argument('--google-cse', '-gc', required=False, help='Google CSE ID')

# Bing arguments
GROUP_BING = PARSER.add_argument_group('Bing Search Engine')
GROUP_BING.add_argument('--bing-key', '-bk', required=False, help='Bing subscription key')


ARGS = PARSER.parse_args(args=None if sys.argv[1:] else ['--help'])

if not ARGS.search_query:
    PARSER.error('--search-query must be specified')

if (not ARGS.google_api or not ARGS.google_cse) and not ARGS.bing_key:
    PARSER.error('at least one search engine must be configured')

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
        response [str]: JSON search object result
    """
    try:
        # https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list
        # Due to API limiting to 10 results returned and a max limit of 100 we loop through till we hit that value
        start = 1
        results = []
        while start <= 100:
            service = build('customsearch', 'v1', developerKey=api_key, cache_discovery=False)
            response = service.cse().list(q=search_term, cx=cse_id, start=start, ** kwargs).execute()  # pylint: disable=no-member

            if response.get('items'):
                results.append({
                    'items': response.get('items')
                })
            else:
                break

            start = start + 10

        return results
    except HttpError as e:
        logging.error(f"[!] Error response from Google Search API - likely incorrect key value(s)")
        verbose_print(f'\t[d]{e}')
        return ''


def extract_google_urls(results):
    """ Extracts URL links from the result JSON

    Args:
        results ([str]): JSON search results

    Returns:
        results_list ([list]): List of URL links parsed
    """
    results_list = []

    for result in results:
        items = result.get('items')

        for item in items:
            results_list.append(item.get('link'))

    return results_list


def bing_search(search_term, sub_key):
    """ Perform Bing search using search term

    Args:
        search_term ([str]): Bing search term string
        sub_key ([str]): Bing subscription key

    Returns:
        response [str]: JSON search object results
    """
    endpoint = "https://api.bing.microsoft.com/v7.0/search"
    params = {'q': search_term}
    headers = {'Ocp-Apim-Subscription-Key': sub_key}

    try:
        response = requests.get(endpoint, headers=headers, params=params)
        verbose_print(f'\t[d]{response}')

        return response.json()
    except Exception:
        logging.error(f"[!] Error response from Bing Search API - likely incorrect key value(s)")
        return ''


def extract_bing_urls(results):
    """ Extracts URL links from the result JSON

    Args:
        results ([str]): JSON search results

    Returns:
        results_list ([list]): List of URL links parsed
    """
    results_list = []
    web_pages = results.get('webPages')

    for item in web_pages.get('value'):
        results_list.append(item.get('url'))

    return results_list


async def check_url_status(session, search_engine, url):
    """ Check status of the URL link provided

    Args:
        session ([aiohttp.ClientSession]): aiohttp session
        search_engine ([str]): search engine string
        url ([str]): url link string

    Returns:
        [type]: [description]
    """
    async with session.get(url) as response:
        http_code = response.status

        if response.status == 200 and ARGS.download:
            f = await aiofiles.open(os.path.basename(url), mode='wb')
            await f.write(await response.read())
            await f.close()

        return {'search_engine': search_engine, 'url': url, 'http_code': http_code}


async def check_all_urls(urls, search_engine):
    """ Async function for checking status of URL links

    Args:
        urls ([str]): list of URLs
        search_engine ([str]): search engine string

    Returns:
        [dict]: returns list of dictionaries
    """
    async with aiohttp.ClientSession() as session:
        tasks = []

        for url in urls:
            tasks.append(
                check_url_status(
                    session,
                    search_engine,
                    url
                )
            )

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        return responses


def save_output_csv(filename, search_results):
    try:
        with open(filename, mode='w') as csv_file:
            field_names = ['search_engine', 'url', 'http_code']
            writer = csv.DictWriter(csv_file, fieldnames=field_names)

            writer.writeheader()

            for item in search_results:
                writer.writerow(item)
    except OSError as e:
        logging.error(f'[!] Creating CSV file - debug info: {e}')


def main():
    """ 
    Main function
    """
    logging.info(f"[i] Fossick v1.0")
    verbose_print(f"Command inputs: {ARGS}")

    # Create empty list to store all results
    results = []

    # Google Search API
    if ARGS.google_api and ARGS.google_cse:
        google_search_results = google_search(ARGS.search_query, ARGS.google_api, ARGS.google_cse)

        if google_search_results:
            google_search_urls = extract_google_urls(google_search_results)
            results.extend(asyncio.run(check_all_urls(google_search_urls, 'Google')))

    # Bing Search API
    if ARGS.bing_key:
        bing_search_results = bing_search(ARGS.search_query, ARGS.bing_key)

        if bing_search_results:
            bing_search_urls = extract_bing_urls(bing_search_results)
            results.extend(asyncio.run(check_all_urls(bing_search_urls, 'Bing')))

    if results:
        # Print to console
        for item in results:
            search_engine = item.get('search_engine')
            url = item.get('url')
            http_code = item.get('http_code')
            logging.info(f'[i] Found Link : {url} \n    Status : HTTP {http_code} \n    Search Engine : {search_engine}')

        # # Save to CSV file
        if ARGS.write_csv:
            filename = "fossick-results.csv"
            save_output_csv(filename, results)
            logging.info(f'[i] Successfully saved output to CSV file search-engine-results.csv')
    else:
        logging.info("[i] No results returned")


if __name__ == "__main__":
    main()
