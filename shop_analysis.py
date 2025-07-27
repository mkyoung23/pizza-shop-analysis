r"""
shop_analysis.py
=================

This script reads a list of pizza shops from a Microsoft Excel workbook and
queries the Google Places API to determine whether each shop has a publicly
available website and whether that website offers direct online ordering
(as opposed to relying solely on third‑party aggregators such as DoorDash,
GrubHub, UberEats or Slice).  The final output is a CSV file containing
the classification results for each shop.

Prerequisites
-------------
* A Google Cloud API key with the **Places API** enabled.  You should set
  an environment variable called `GOOGLE_API_KEY` with your API key
  before running this script.
* Python packages: `pandas`, `requests`.  Install with
  ``pip install pandas requests``.

Usage
-----
```
python shop_analysis.py --input "Store Map.xlsx" --output results.csv
```

The script reads all relevant sheets from the Excel workbook (``All``,
``Multi Location Shops`` and ``OO Partners``) and merges them into a single
list of unique shop names and locations.  For each shop it performs two
API calls: one to ``findplacefromtext`` to obtain the place ID, and another
to ``place/details`` to fetch the website URL.  It then classifies the
website as either ``direct`` or ``third_party`` depending on whether the
domain belongs to a known aggregator.

The output CSV includes the following columns:

```
ShopID,AccountName,BillingCity,BillingZip,Website,HasWebsite,DirectOrdering,Note
```

* ``HasWebsite`` is ``True`` if the Google Places details contain a
  ``website`` field, ``False`` otherwise.
* ``DirectOrdering`` is ``True`` if ``HasWebsite`` is ``True`` **and** the
  website domain does not belong to a known third‑party aggregator.  If
  there is no website or the website domain is an aggregator, this
  column is ``False``.
* ``Note`` contains a short explanation for shops without websites or with
  suspected third‑party ordering only.

If no API key is provided, the script will skip API calls and produce a
CSV listing the unique shops without classification.  You can still use
this CSV as a starting point for manual checking.

"""

import os
import argparse
import csv
import time
from urllib.parse import urlparse
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests


# List of domains that represent third‑party ordering providers.  If a
# restaurant's website resolves to one of these domains, we consider
# them as not having their own direct ordering (i.e., they rely on
# aggregators).  This list can be extended as needed.
THIRD_PARTY_DOMAINS = {
    "doordash.com",
    "grubhub.com",
    "ubereats.com",
    "seamless.com",
    "postmates.com",
    "slicelife.com",
    "slicelife.onelink.me",
    "postmates.com",
    "bestcafes.online",
}


def read_shops_from_excel(xlsx_path: str) -> pd.DataFrame:
    """Read relevant sheets from the Excel file and return a DataFrame
    with unique shop information.

    Parameters
    ----------
    xlsx_path : str
        Path to the Excel workbook.

    Returns
    -------
    pd.DataFrame
        DataFrame containing unique shops with their names, IDs, cities and
        postal codes.
    """
    # Load the workbook
    xls = pd.ExcelFile(xlsx_path)
    # Sheets that contain shop lists
    sheet_names = [
        "All",
        "Multi Location Shops",
        "OO Partners",
    ]
    dfs = []
    for sheet in sheet_names:
        if sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet)
            # Standardise column names
            df = df.rename(
                columns={
                    "Shop ID": "ShopID",
                    "Account Name": "AccountName",
                    "Billing City": "BillingCity",
                    "Billing Zip/Postal Code": "BillingZip",
                }
            )
            # Keep only relevant columns
            subset = df[[
                "ShopID" if "ShopID" in df.columns else None,
                "AccountName" if "AccountName" in df.columns else None,
                "BillingCity" if "BillingCity" in df.columns else None,
                "BillingZip" if "BillingZip" in df.columns else None,
            ]].copy()
            # Drop fully missing rows
            subset = subset.dropna(how="all")
            dfs.append(subset)
    # Concatenate and remove duplicates
    all_shops = pd.concat(dfs, ignore_index=True)
    # Remove duplicate AccountName entries
    all_shops = all_shops.drop_duplicates(subset=["AccountName"])
    # Reset index
    all_shops.reset_index(drop=True, inplace=True)
    return all_shops


def query_google_places(api_key: str, query: str) -> Optional[str]:
    """Use the Google Places API to find a place ID for a given query.

    Parameters
    ----------
    api_key : str
        Your Google API key.
    query : str
        The text query used to find the place.

    Returns
    -------
    Optional[str]
        The place ID if found, else ``None``.
    """
    base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    params = {
        "key": api_key,
        "input": query,
        "inputtype": "textquery",
        "fields": "place_id",
    }
    try:
        r = requests.get(base_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0].get("place_id")
    except Exception:
        # Return None on any failure
        return None
    return None


def get_place_details(api_key: str, place_id: str) -> Dict[str, Optional[str]]:
    """Retrieve selected place details from Google Places API.

    Parameters
    ----------
    api_key : str
        Your Google API key.
    place_id : str
        The unique place ID to look up.

    Returns
    -------
    dict
        Dictionary containing the website URL and the Google Maps URL for the
        place.  Keys are ``website`` and ``url``; values may be ``None``.
    """
    base_url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "key": api_key,
        "place_id": place_id,
        "fields": "website,url",
    }
    try:
        r = requests.get(base_url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json().get("result", {})
        website = data.get("website")
        url = data.get("url")
        return {"website": website, "url": url}
    except Exception:
        return {"website": None, "url": None}


def classify_website(website: Optional[str]) -> Tuple[bool, bool]:
    """Classify a website based on presence and domain.

    Parameters
    ----------
    website : Optional[str]
        The website URL returned from Google Places.

    Returns
    -------
    tuple
        ``(has_website, direct_ordering)`` where ``has_website`` is
        ``True`` if a website URL is present, and ``direct_ordering`` is
        ``True`` if the website domain does not belong to a known
        third‑party aggregator.
    """
    if not website:
        return (False, False)
    try:
        domain = urlparse(website).netloc
        # Remove 'www.' prefix
        domain = domain.lower().lstrip("www.")
        if any(domain.endswith(third) for third in THIRD_PARTY_DOMAINS):
            return (True, False)
        else:
            return (True, True)
    except Exception:
        return (True, False)


def analyse_shops(input_file: str, output_file: str) -> None:
    """Perform the full analysis on the shops list and write results to CSV.

    Parameters
    ----------
    input_file : str
        Path to the Excel workbook containing shop lists.
    output_file : str
        Path to the CSV file that will be written with the results.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(
            "WARNING: No GOOGLE_API_KEY environment variable found. The script will "
            "proceed without API calls and mark all shops as unknown."
        )

    # Read the list of shops
    shops_df = read_shops_from_excel(input_file)

    # Prepare CSV output
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        # Header
        writer.writerow([
            "ShopID",
            "AccountName",
            "BillingCity",
            "BillingZip",
            "Website",
            "HasWebsite",
            "DirectOrdering",
            "Note",
        ])

        for idx, row in shops_df.iterrows():
            shop_id = row.get("ShopID")
            account_name = row.get("AccountName")
            city = row.get("BillingCity")
            zip_code = row.get("BillingZip")
            website_url = None
            has_site = False
            direct = False
            note = ""

            if api_key:
                # Build query string: include city and state to improve accuracy
                query = f"{account_name}, {city if pd.notna(city) else ''}, MA"
                place_id = query_google_places(api_key, query)
                if place_id:
                    details = get_place_details(api_key, place_id)
                    website_url = details.get("website")
                    has_site, direct = classify_website(website_url)
                    if not has_site:
                        note = "No website"
                    elif not direct:
                        note = "Website appears to be third‑party ordering"
                else:
                    note = "Place not found"
            else:
                note = "API key not provided"

            writer.writerow([
                shop_id,
                account_name,
                city,
                zip_code,
                website_url,
                has_site,
                direct,
                note,
            ])
            # Throttle requests to respect API usage limits (adjust as needed)
            if api_key:
                time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(description="Analyse pizza shops for website and ordering.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input Excel file (e.g., Store Map.xlsx)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to output CSV file",
    )
    args = parser.parse_args()
    analyse_shops(args.input, args.output)


if __name__ == "__main__":
    main()
