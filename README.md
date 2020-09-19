YNAB Comparator
===============

The YNAB Comparator Script can be used to find errors in your "YNABing".
This script offers a fast way to do a first rough search for the culprit
transactions, in the case where the balance in your bank account does not
match the balance in YNAB, 

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
If you provide a YNAB API Token in `$repo/data/token.api`, the script will attempt to pull the data straight from YNAB.

If you do not provide a YNAB API Token, you need to export the YNAB data yourself.
1) The YNAB export is a zip archive. You only need the Register-tsv.
2) Save it as `$repo/data/ynab.tsv`

## SWEDBANK
1) Save the Swedbank export as `$repo/data/swedbank.csv`
2) Remove the first row of the exported csv.

## ICA
1) Save the ICA export as `$repo/data/ica.csv`

## Run Script
`python ynab_comp/ynab_comp.py --budget-name $YNAB-budget-name --filter-date "YYYY-MM-DD"`

* `--budget-name` is the name of the budget, in YNAB
* `--filter-date` is the earliest date from where transactions should be compared
