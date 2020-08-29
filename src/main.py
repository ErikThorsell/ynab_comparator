#!/usr/bin/env python3.7.3
# -*- coding: utf-8 -*-
#
# Imports
import math

import pandas as pd

###############################################################################
#                                  FUNCTIONS                                  #
###############################################################################
def extract_ynab_df(ynab_tsv, account, filter_date):
  """Extract the interesting data from the YNAB .tsv.

  Extracts: [Date, Payee, Outflow, Inflow], from the account specified
  """
  ynab_df = pd.read_csv(ynab_tsv, sep="\t")

  filtered_ynab_df = ynab_df.loc[
      (ynab_df["Date"] >= filter_date) &
      (ynab_df["Account"] == account)
  ][["Date", "Payee", "Outflow", "Inflow"]]
  filtered_ynab_df.columns = ["Date", "Description", "Outflow", "Inflow"]

  merged_ynab_df = pd.DataFrame(columns=["Date", "Description", "Amount"])
  for idx, row in filtered_ynab_df.iterrows():
    amount = float(row["Inflow"].rstrip("kr").replace(",",".")) - float(row["Outflow"].rstrip("kr").replace(",","."))
    merged_ynab_df.loc[idx] = [row["Date"], row["Description"].lower(), amount]

  print(f"Extracted {len(merged_ynab_df.index)} entries from YNAB")

  return merged_ynab_df


def extract_swedbank_df(swedbank_csv, filter_date):
  """Extract the interesting data from the Swedbank .csv."""
  # Stupid Swedbank does not follow CSV Standards
  # Remember to remove the first line from the file!

  swedbank_df = pd.read_csv(swedbank_csv, encoding="unicode_escape")
  saldo = float(swedbank_df["Bokfört saldo"].iloc[0])
  print(f"Swedbank Saldo: {saldo} SEK")

  filtered_swedbank_df = swedbank_df.loc[(swedbank_df["Bokföringsdag"] >= filter_date)][["Bokföringsdag", "Beskrivning", "Belopp"]]
  filtered_swedbank_df.columns = ["Date", "Description", "Amount"]
  filtered_swedbank_df["Description"] = filtered_swedbank_df["Description"].str.lower()
  filtered_swedbank_df["Amount"] = filtered_swedbank_df["Amount"].astype(float)

  print(f"Extracted {len(filtered_swedbank_df.index)} entries from Swedbank")

  return filtered_swedbank_df


def extract_ica_df(ica_csv, filter_date):
  """Extract the interesting data from the ICA .csv."""
  ica_df = pd.read_csv(ica_csv, sep=";")

  saldo = "nan"
  idx = 0

  # ICA exports "waiting transactions"
  # We loop until we find the first "none NaN" row
  while True:
      saldo = str(ica_df["Saldo"].iloc[idx])
      if saldo != "nan":
          break
      idx += 1

  saldo = float(saldo.replace("kr", "").replace(",", ".").replace(" ", ""))
  print(f"ICA Saldo: {saldo} SEK")

  filtered_ica_df = ica_df.loc[(ica_df["Datum"] >= filter_date)][["Datum", "Text", "Belopp"]]
  filtered_ica_df.columns = ["Date", "Description", "Amount"]
  filtered_ica_df["Description"] = filtered_ica_df["Description"].str.lower()
  filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace("kr", ""))
  filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace(",", "."))
  filtered_ica_df["Amount"] = filtered_ica_df["Amount"].map(lambda a: a.replace(" ", ""))
  filtered_ica_df["Amount"] = filtered_ica_df["Amount"].astype(float)

  print(f"Extracted {len(filtered_ica_df.index)} entries from ICA")

  return filtered_ica_df


def compare_frames(ynab_df, bank_df, printing=False):
  """"""

  not_found_ynab_df = pd.DataFrame(columns=["Date", "Description", "Amount"])

  for idx_bank, row_bank in bank_df.iterrows():
    found = False
    bank_amount = row_bank["Amount"]

    for idx_ynab, row_ynab in ynab_df.iterrows():
      if row_ynab["Amount"] == bank_amount:
        if printing:
          print(f"{bank_amount} | {row_ynab['Description']} | {row_bank['Description']}")
        ynab_df.drop(idx_ynab, inplace=True)
        found = True
        break

    if not found:
      if printing:
        print(f"Did not find: {bank_amount} | {row_bank['Description']}")
      missing_row = {
        "Date": row_bank["Date"],
        "Description": row_bank["Description"],
        "Amount": bank_amount
      }
      not_found_ynab_df = not_found_ynab_df.append(missing_row, ignore_index=True)

  return not_found_ynab_df



###############################################################################
#                                    MAIN                                     #
###############################################################################
def main():

  filter_date = "2020-06-01"
  pairs = dict()

  # SWEDBANK
  print("\nParsing data from Swedbank")
  ynab_swedbank = extract_ynab_df("data/ynab.tsv", "Checking", filter_date)
  swedbank = extract_swedbank_df("data/swedbank.csv", filter_date)
  pairs["swedbank"] = (ynab_swedbank, swedbank)

  # ICA
  print("\nParsing data from ICA")
  ynab_ica = extract_ynab_df("data/ynab.tsv", "ICA Banken", filter_date)
  ica = extract_ica_df("data/ica.csv", filter_date)
  pairs["ica"] = (ynab_ica, ica)

  # COMPARE FRAMES
  for key in pairs:
      print("\n\n" + ">"*20 + f" {key.upper()} " + "<"*20)
      ynab, bank = pairs[key]

      in_bank_not_ynab = compare_frames(ynab, bank, printing=False)

      if not in_bank_not_ynab.empty:
          print(f" > The following transactions were found in the {key.upper()} Export, but not in YNAB")
          print(in_bank_not_ynab)

      in_ynab_not_bank = compare_frames(bank, ynab, printing=False)

      if not in_ynab_not_bank.empty:
          print(f"\n > The following transactions were found in YNAB, but not in the {key.upper()} Export")
          print(in_ynab_not_bank)

      if in_bank_not_ynab.empty and in_ynab_not_bank.empty:
          print(f"{key.upper()} has no deviating transactions!\n")

###############################################################################
#                                    RUN                                      #
###############################################################################


if __name__ == "__main__":
  main()

