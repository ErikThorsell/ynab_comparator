from typing import List
from loguru import logger
from requests import get


class YNABError(Exception):
    pass


def get_api_token() -> str:
    """Read the data/token.api file and return the token."""
    try:
        with open("data/token.api") as api_f:
            return api_f.read().strip()
    except FileNotFoundError:
        return None


def download_ynab_data(token: str, budget_name: str, filter_date: str) -> None:
    """Download the YNAB data of interest and store it as data/ynab_api.tsv.

    Args:
        token: The YNAB API Token (acquired at their development page)
        budget_name: The name of the YNAB Budget to fetch transactions from
        filter_date: The earliest date to consider transactions from
    """

    API_URL = "https://api.youneedabudget.com/v1"

    logger.info(f"Downloading YNAB data for budget: {budget_name}")
    ynab_budget = get_ynab_budget(API_URL, token, budget_name)

    ynab_budget_id = ynab_budget["id"]
    ynab_budget_transactions = get_ynab_budget_transactions(
        API_URL, token, ynab_budget_id, filter_date
    )
    store_ynab_transactions_as_csv(ynab_budget_transactions)


def get_ynab_budget(api_url: str, token: str, budget_name: str) -> str:
    """Ensure the budget of interest is available in YNAB.

    Args:
        api_url: URL for YNAB API
        token: The YNAB API Token (acquired at their development page)
        budget_name: The name of the YNAB Budget to fetch transactions from
    Returns:
        Budget JSON object from which the budget id can be fetched
    """

    headers = {
        "Authorization": f"Bearer {token}",
    }

    budget_url = api_url + "/budgets"

    response = get(budget_url, headers=headers)
    json_content = response.json()

    for budget in json_content["data"]["budgets"]:
        if budget["name"] == budget_name:
            return budget

    raise YNABError(f"Unable to find budget: {budget_name}")


def get_ynab_budget_transactions(
    api_url: str, token: str, budget_id: str, filter_date=None
) -> List[str]:
    """

    Args:
        api_url: URL for YNAB API
        token: The YNAB API Token (acquired at their development page)
        budget_id: The id of the YNAB Budget to fetch transactions for
        filter_date: The earliest date to consider transactions from
    Returns:
        A list of JSON objects where each object corresponds to a transaction
    """

    headers = {
        "Authorization": f"Bearer {token}",
    }
    params = {}

    query_url = api_url + f"/budgets/{budget_id}/transactions"
    if filter_date:
        params["since_date"] = filter_date

    response = get(query_url, headers=headers, params=params)
    json_content = response.json()
    json_transactions = json_content["data"]["transactions"]

    logger.info(f"Fetched {len(json_transactions)} transactions")
    return json_transactions


def store_ynab_transactions_as_csv(ynab_transactions: str):
    """Store the list of transactions in a .tsv file.

    This function might seem like a mess; but I could not find any
    other way to make the resulting .tsv the _exact_ same as the .tsv
    export from the YNAB Web App.

    Quotation marks suck.

    Args:
        ynab_transactions: A list of JSON objects where each object corresponds to a transaction
    """
    ynab_tsv_path = "data/ynab_api.tsv"
    logger.info(f"Writing YNAB Transactions to: {ynab_tsv_path}")

    with open(ynab_tsv_path, "w", newline="") as csv_fh:

        csv_fh.write(
            '"Account"\t'
            + '"Flag"\t'
            + '"Date"\t'
            + '"Payee"\t'
            + '"Category Group/Category"\t'
            + '"Category Group"\t'
            + '"Category"\t'
            + '"Memo"\t'
            + '"Outflow"\t'
            + '"Inflow"\t'
            + '"Cleared"\n'
        )

        for transaction in ynab_transactions:

            # Amount is given as:
            #   1863600 instead of 1863.600
            #   -33710 instead of -33.710
            before_dec = str(transaction["amount"])[:-3]
            after_dec = str(transaction["amount"])[-3:]
            amount = f"{before_dec},{after_dec[:-1]}kr"

            if amount[0] == "-":
                outflow = amount[1:]
                inflow = "0,00kr"
            else:
                inflow = amount
                outflow = "0,00kr"

            csv_fh.write(
                f"\"{transaction['account_name']}\"\t"
                + f"\"{transaction['flag_color']}\"\t"
                + f"\"{transaction['date']}\"\t"
                + f"\"{transaction['payee_name']}\"\t"
                + f"\"{transaction['category_name']}\"\t"
                + f"\"{transaction['category_name']}\"\t"
                + f"\"{transaction['category_name']}\"\t"
                + f"\"{transaction['memo']}\"\t"
                + f"{outflow}\t"
                + f"{inflow}\t"
                + f"\"{transaction['cleared']}\"\n"
            )
