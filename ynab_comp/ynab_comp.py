import argparse
import sys

from loguru import logger

from dataframes import compare_ynab_to_bank, extract_ica_df, extract_swedbank_df
from ynab_api import download_ynab_data, get_api_token


def main(args):
    """The main function of the script YNAB Comparison.

    In order to expand the functionality of the script you need to add a new
    bank parser function (extract_bank-name_df) and add a new quadruple to the
    LIST_OF_BANKS.

    Args:
        Budget Name: YNAB budget name
        Filter Date: Earliest date to take into consideration when parsing data
    """

    # (YNAB Account Name, Path to data file, Name of bank, Function that parses data file into a DataFrame)
    LIST_OF_BANKS = [
        ("Checking", "data/swedbank.csv", "Swedbank", extract_swedbank_df),
        ("ICA Banken", "data/ica.csv", "ICA Banken", extract_ica_df),
    ]

    # Query YNAB API for data
    if api_token := get_api_token():
        download_ynab_data(api_token, args.budget_name, args.filter_date)
        ynab_tsv = "data/ynab_api.tsv"
    else:
        logger.warning(
            "Unable to find API Token in data/token.api. "
            "Continuing under the assumption that you have up to date "
            "YNAB data available in data/ynab.tsv."
        )
        ynab_tsv = "data/ynab.tsv"

    for account, bank_file, bank, extraction_function in LIST_OF_BANKS:
        compare_ynab_to_bank(
            ynab_tsv,
            account,
            bank_file,
            bank,
            extraction_function,
            args.filter_date,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter-date", required=True, help="Earliest date to take into consideration.")
    parser.add_argument(
        "--budget-name",
        required=True,
        help="Name of YNAB Budget to use, if querying the YNAB API.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        required=False,
        action="store_true",
        help="",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    main(args)
