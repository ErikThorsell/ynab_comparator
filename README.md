YNAB Comparator
===============

The YNAB Comparator Script can be used to find errors in your "YNABing".
If the balance in your bank account does not match the balance in YNAB, this
script offers a fast way to do a first rough search for the culprit
transactions.

The script compares each transaction in your YNAB export to each transaction in
your bank export.
(Supported banks below.)
The script also does the inverse comparison.

Compare the outputs and you will likely spot the (hopefully) few transactions
that are erroneous.

# Supported Banks

This script supports comparing the exports from YNAB (web version) with the
exports from:

* Swedbank
* ICA Banken

# USAGE

## YNAB
1) The YNAB export is a zip archive. You only need the Register-tsv.
2) Save it as `$repo/data/ynab.tsv`

## SWEDBANK
1) Save the Swedbank export as `$repo/data/swedbank.csv`
2) Remove the first row of the exported csv.

## ICA
1) Save the ICA export as `$repo/data/ica.csv`

## Run Script
Edit the `filter_date` in the script (`src/main.py`). The `filter_date` denotes
the oldest transactions that should be compared.

`python src/main.py`
