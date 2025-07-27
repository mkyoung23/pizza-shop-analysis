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
python shop_analysis.py --input Store\ Map.xlsx --output results.csv
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


def generate_messages(account_name: str, has_website: bool, direct_ordering: bool) -> Tuple[str, str, str]:
    """Generate email subject, email body and SMS body for a shop.

    The messaging is customised based on whether the shop has its own website
    and whether it accepts direct online orders.  The goal is to
    highlight Slice's strengths—custom websites, phone ordering, discounted
    delivery, pizzeria‑specific POS and advanced marketing—depending on the
    shop's current state.

    Parameters
    ----------
    account_name : str
        Name of the pizzeria.
    has_website : bool
        Whether the shop has any website listed on Google.
    direct_ordering : bool
        Whether the website allows direct ordering (i.e., not through third‑party
        aggregators).

    Returns
    -------
    tuple
        A tuple of (email_subject, email_body, sms_body).
    """
    # Base salutation
    salutation = f"Hi {account_name},"
    if not has_website:
        subject = "Grow your pizzeria with a custom website and phone ordering"
        body = (
            f"{salutation}\n\n"
            "I noticed your pizzeria doesn’t have a website listed online. "
            "With Slice, you can get a tailor‑made website and a phone ordering "
            "solution that puts you in control of your customer relationships. "
            "Our platform even offers discounted delivery and a pizzeria‑specific POS system to help you run your business more smoothly."
        )
        sms = (
            f"{account_name}: We can build you a custom website and phone ordering "
            "solution through Slice, plus discounted delivery and a POS built for pizzerias."
        )
    elif has_website and not direct_ordering:
        subject = "Boost profits with direct ordering and discounted delivery"
        body = (
            f"{salutation}\n\n"
            "It looks like your current website relies on third‑party ordering apps. "
            "Slice lets you own the entire ordering experience with direct online and phone ordering. "
            "We provide integrated discounted delivery and a POS designed specifically for independent pizzerias, so you keep more margin and delight your customers."
        )
        sms = (
            f"{account_name}: Let’s get you off third‑party apps. Slice offers direct online/phone ordering with discounted delivery and a pizzeria‑specific POS."
        )
    else:
        subject = "Take your online presence further with Slice’s marketing & POS"
        body = (
            f"{salutation}\n\n"
            "Great job having your own direct ordering! Slice can help you go even further "
            "with advanced advertising services, a powerful owner’s app, and a POS built for pizzerias. "
            "We also host pizzeria‑owner events and provide industry reports to help you stay ahead."
        )
        sms = (
            f"{account_name}: You’re already direct—let’s accelerate growth. Slice offers marketing, a custom POS, and owner resources just for pizzerias."
        )
    return subject, body, sms



def analyse_shops(
    input_file: str,
    output_file: str,
    message_output_file: Optional[str] = None,
) -> None:
    """Perform the full analysis on the shops list and optionally write outreach messages.

    Parameters
    ----------
    input_file : str
        Path to the Excel workbook containing shop lists.
    output_file : str
        Path to the CSV file that will be written with the classification results.
    message_output_file : str, optional
        Path to a CSV file that will be written with outreach messages for each shop.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(
            "WARNING: No GOOGLE_API_KEY environment variable found. The script will "
            "proceed without API calls and mark all shops as unknown."
        )

    # Read the list of shops
    shops_df = read_shops_from_excel(input_file)

    # Prepare outputs
    classifications: List[List] = []
    messages: List[List] = []

    for idx, row in shops_df.iterrows():
        shop_id = row.get("ShopID")
        account_name = row.get("AccountName")
        city = row.get("BillingCity")
        zip_code = row.get("BillingZip")
        website_url: Optional[str] = None
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

        classifications.append([
            shop_id,
            account_name,
            city,
            zip_code,
            website_url,
            has_site,
            direct,
            note,
        ])

        # Generate outreach messages
        subj, body, sms = generate_messages(account_name, has_site, direct)
        messages.append([
            shop_id,
            account_name,
            subj,
            body,
            sms,
        ])
        # Throttle requests to respect API usage limits (adjust as needed)
        if api_key:
            time.sleep(0.2)

    # Write classifications to CSV
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
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
        writer.writerows(classifications)

    # Optionally write messages to CSV
    if message_output_file:
        with open(message_output_file, "w", newline="", encoding="utf-8") as fmsg:
            writer = csv.writer(fmsg)
            writer.writerow([
                "ShopID",
                "AccountName",
                "EmailSubject",
                "EmailBody",
                "SmsBody",
            ])
            writer.writerows(messages)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Analyse pizza shops to determine whether they have websites and direct ordering, "
            "and optionally generate personalised outreach messages."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to the input Excel file (e.g., Store Map.xlsx)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to the classification output CSV file",
    )
    parser.add_argument(
        "--messages",
        default=None,
        help=(
            "Optional path to a CSV file where outreach messages (email and SMS) "
            "will be written. If not provided, messages will not be saved."
        ),
    )
    args = parser.parse_args()
    analyse_shops(args.input, args.output, args.messages)


if __name__ == "__main__":
    main()
