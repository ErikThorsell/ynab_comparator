"""Module for everything related to Pandas DataFrames."""
from datetime import datetime
from typing import Callable
from loguru import logger
import sys

import pandas as pd
from thefuzz import fuzz


def extract_ynab_df(ynab_tsv: str, account: str, filter_date: str) -> pd.DataFrame:
    """Extract the interesting data from the YNAB .tsv.

    Extracts: [Date, Payee, Outflow, Inflow, Memo], from the account specified,
    then converts the data into a DataFrame with Columns [Date, Description, Amount, Memo].

    Args:
        ynab_tsv: Path to the .tsv file
        account: Name of the YNAB Account for which you want to extract transactions
        filter_date: Earliest date to take into consideration when parsing
    """
    ynab_df = pd.read_csv(ynab_tsv, sep="\t", index_col=False)

    filtered_ynab_df = ynab_df.loc[(ynab_df["Date"] >= filter_date) & (ynab_df["Account"] == account)]

    logger.debug(f"Sample of YNAB data for account {account}:\n{filtered_ynab_df.head(5)}")

    data_of_interest_df = filtered_ynab_df[["Date", "Payee", "Outflow", "Inflow", "Memo"]]
    data_of_interest_df.columns = ["Date", "Description", "Outflow", "Inflow", "Memo"]
    logger.debug(f"Parsed YNAB data:\n{data_of_interest_df.head(5)}")

    # It is important that every DataFrame have the same Column names (Date, Description, Amount, Memo)
    parsed_df = pd.DataFrame(columns=["Date", "Description", "Amount", "Memo"])

    for idx, row in data_of_interest_df.iterrows():
        inflow = row["Inflow"].rstrip("kr").replace(",", ".")
        outflow = row["Outflow"].rstrip("kr").replace(",", ".")
        try:  # you'll end up in the except if you have an empty row in YNAB
            amount = float(inflow) - float(outflow)
        except ValueError as e:
            logger.error(f"Unable to parse inflow/outflow: {inflow}/{outflow}.")
            logger.error(f"Error: {e}")
            raise

        parsed_df.loc[idx] = [row["Date"], row["Description"].lower(), amount, row["Memo"]]

    logger.info(f"Extracted {len(parsed_df.index)} entries from YNAB, for account {account}.")
    logger.debug(f"YNAB Data:\n{parsed_df.head(5)}")

    return parsed_df


def extract_swedbank_df(swedbank_csv: str, filter_date: str) -> pd.DataFrame:
    """Extract the interesting data from a Swedbank .csv.

    Extracts the [Date, Description, Amount] from the .csv.

    ~ Known issue with CSV File ~
    The Swedbank "csv" isn't a very good CSV.

        1. It has an extra line at the top of the file which is not part of
        the actual data.
        2. The file is encoded using cp1252 (Windows 1252 encoding).

    If you just download the file and run the script, the script attempts to
    open the file, remove the first line, and re-encode the file as UTF-8.
    However, if you remove the first line yourself but save the file as
    cp1252, Pandas must open the file with unicode_espace. (Hence the try/except.)

    I hope this makes the parsing more robust.

    Args:
        swedbank_csv: Path to the .csv file
        filter_date: Earliest date to take into consideration when parsing
    """

    # Encoding fixing and data stripping (explained in docstring)
    with open(swedbank_csv, encoding="cp1252") as sb_csv:
        data = sb_csv.readlines()

    if "* Transaktioner" in data[0]:
        data = "".join(data[1:])
        with open(swedbank_csv, "w", encoding="utf-8") as sb_csv:
            sb_csv.write(data)

    try:
        swedbank_df = pd.read_csv(swedbank_csv)
    except KeyError:
        swedbank_df = pd.read_csv(swedbank_csv, encoding="unicode_escape")
    # End of Encoding and data stripping

    saldo = float(swedbank_df["Bokfört saldo"].iloc[0])
    logger.info(f"Swedbank Saldo: {saldo} SEK")

    filtered_swedbank_df = swedbank_df.loc[(swedbank_df["Bokföringsdag"] >= filter_date)][
        ["Bokföringsdag", "Beskrivning", "Referens", "Belopp"]
    ]
    filtered_swedbank_df.columns = ["Date", "Description", "Reference", "Amount"]
    filtered_swedbank_df["Description"] = filtered_swedbank_df["Description"].str.lower()
    filtered_swedbank_df["Reference"] = filtered_swedbank_df["Reference"].str.lower()
    filtered_swedbank_df["Amount"] = filtered_swedbank_df["Amount"].astype(float)

    logger.info(f"Extracted {len(filtered_swedbank_df.index)} entries from Swedbank")
    logger.debug(f"Data:\n{filtered_swedbank_df.head(5)}")

    return filtered_swedbank_df


def extract_ica_df(ica_csv: str, filter_date: str) -> pd.DataFrame:
    """Extract the interesting data from a ICA Banken .csv.

    Extracts the [Date, Description, Amount] from the .csv.

    Args:
        ica_csv: Path to the .csv file
        filter_date: Earliest date to take into consideration when parsing
    """
    ica_df = pd.read_csv(ica_csv, sep=";")

    idx = 0

    # ICA exports "waiting transactions"
    # We loop until we find the first "none NaN" row
    while True:
        saldo = str(ica_df["Saldo"].iloc[idx])
        if saldo != "nan":
            break
        idx += 1

    saldo = float(saldo.replace("kr", "").replace(",", ".").replace(" ", ""))
    logger.info(f"ICA Saldo: {saldo} SEK")

    filtered_ica_df = ica_df.loc[(ica_df["Datum"] >= filter_date)][["Datum", "Text", "Belopp"]]

    filtered_ica_df.columns = ["Date", "Description", "Amount"]
    filtered_ica_df["Description"] = filtered_ica_df["Description"].str.lower()

    # The Reference column does not exist, but we use it in the Swedbank export
    # hence we add it here (empty) for consistency.
    filtered_ica_df["Reference"] = ""

    # This is hacky, and tacky, but it works...
    filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace("kr", ""))
    filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace(",", "."))
    filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace(" ", ""))
    filtered_ica_df["Amount"] = filtered_ica_df["Amount"].astype(float)

    logger.info(f"Extracted {len(filtered_ica_df.index)} entries from ICA")

    return filtered_ica_df


def compare_frames(frame_1: pd.DataFrame, frame_2: pd.DataFrame, printing: bool = False) -> pd.DataFrame:
    """Check whether transactions in frame 1 are also present in frame 2.

    Args:
        frame_1: The DataFrame used as "the truth".
        frame_2: The DataFrame in which transactions can be missing.
    Returns:
        A DataFrame containing the transactions from frame_1, not found in frame_2.
    """

    not_found = pd.DataFrame(columns=["Date", "Description", "Amount"])

    for _, transaction_1 in frame_1.iterrows():
        logger.debug(
            f"Verifying transaction: {transaction_1['Description']} from {transaction_1['Date']} @ {transaction_1['Amount']}"
        )

        found = False
        amount_1 = transaction_1["Amount"]

        matching_amount = frame_2.loc[frame_2["Amount"] == amount_1]
        logger.debug(f" > Found {len(matching_amount)} rows with amount {amount_1}")

        for idx_2, transaction_2 in matching_amount.iterrows():
            logger.debug(
                f" > {transaction_1['Description']} and {transaction_2['Description']} have the same amount: {amount_1}"
            )

            if len(matching_amount) == 1:
                logger.debug(f" >> Considering uniqueness to be enough. Dropping!")
                frame_2.drop(idx_2, inplace=True)
                found = True
                break

            t1 = datetime.strptime(transaction_1["Date"], "%Y-%m-%d")
            t2 = datetime.strptime(transaction_2["Date"], "%Y-%m-%d")
            t_diff = t1 - t2
            logger.debug(f" > The difference in time between the two transactions is: {t_diff.days}")

            if abs(t_diff.days) > 7:
                logger.debug(f" >> Considering the transactions to be too distant. Moving on.")
                continue

            # Compare with Description
            f_ratio = fuzz.partial_ratio(transaction_1["Description"], transaction_2["Description"])
            logger.debug(
                f" > {transaction_1['Description']} and {transaction_2['Description']} have Fuzz Ratio: {f_ratio}"
            )

            if f_ratio > 65:
                logger.debug(f" >> Considering the transactions to be similar enough. Dropping!")
                frame_2.drop(idx_2, inplace=True)
                found = True
                break

            # Compare Description in bank statement with Memo field in YNAB
            if "Memo" in transaction_2 and not pd.isna(transaction_2["Memo"]):
                logger.debug(f" > Unable to find match in Description, trying Memo: {transaction_2['Memo']}")
                f_ratio = fuzz.partial_ratio(transaction_1["Description"], transaction_2["Memo"])
                logger.debug(
                    f" > {transaction_1['Description']} and {transaction_2['Memo']} have Fuzz Ratio: {f_ratio}"
                )

                if f_ratio > 65:
                    logger.debug(f" >> Considering the transactions to be similar enough. Dropping!")
                    frame_2.drop(idx_2, inplace=True)
                    found = True
                    break

                # Compare "Reference" in bank statement with Memo field in YNAB
                if not pd.isna(transaction_1['Reference']):
                    logger.debug(f" > Unable to find match in Description, trying Reference: {transaction_1['Reference']}")
                    f_ratio = fuzz.partial_ratio(transaction_1["Reference"], transaction_2["Memo"])
                    logger.debug(f" > {transaction_1['Reference']} and {transaction_2['Memo']} have Fuzz Ratio: {f_ratio}")

                    if f_ratio > 65:
                        logger.debug(f" >> Considering the transactions to be similar enough. Dropping!")
                        frame_2.drop(idx_2, inplace=True)
                        found = True
                        break

        if not found:
            logger.warning(f" > Did not find: {amount_1} | {transaction_1['Description']} @ {transaction_1['Date']}")
            missing_row = {
                "Date": transaction_1["Date"],
                "Description": transaction_1["Description"],
                "Amount": amount_1,
            }
            not_found = not_found.append(missing_row, ignore_index=True)

    return not_found


def compare_ynab_to_bank(
    ynab_tsv: str,
    ynab_account: str,
    bank_file: str,
    bank_name: str,
    extraction_function: Callable[[str, str], pd.DataFrame],
    filter_date: str,
) -> None:
    """Compare a YNAB .tsv file to a bank's transaction excerpt.

    Args:
        ynab_tsv: Path to YNAB .tsv file
        ynab_account: Name of YNAB Account of interest
        bank_file: Path to the bank transaction file
        bank_name: Name of bank
        extraction_function: The extraction function required to parse the bank_file
        filter_date: Earliest date to take into consideration

    """
    logger.info(f"Comparing YNAB Account: {ynab_account}, to data from {bank_name}.")

    ynab = extract_ynab_df(ynab_tsv, ynab_account, filter_date)
    bank = extraction_function(bank_file, filter_date)

    # Just ensure both frames are sorted in the same direction
    ynab.sort_values(by="Date")
    bank.sort_values(by="Date")

    in_bank_not_ynab = compare_frames(bank, ynab, printing=False)

    if not in_bank_not_ynab.empty:
        logger.warning(
            f"There are {len(in_bank_not_ynab)} transactions found in the " f"{bank_name} export, but not in YNAB."
        )
    else:
        logger.info(f"There are no transactions in {bank_name} that are not also in YNAB.")

    in_ynab_not_bank = compare_frames(ynab, bank, printing=False)

    if not in_ynab_not_bank.empty:
        logger.warning(
            f"There are {len(in_ynab_not_bank)} transactions found in YNAB, but not in the {bank_name} export."
        )
    else:
        logger.info(f"There are no transactions in YNAB that are not also in {bank_name}.")

    if in_bank_not_ynab.empty and in_ynab_not_bank.empty:
        logger.info(f"{bank_name} has no deviating transactions!")
