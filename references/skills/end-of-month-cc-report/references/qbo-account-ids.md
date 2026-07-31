# QBO credit-card account IDs

Pull each account with `quickbooks_transaction_detail_by_account`. **`account_id` is the QBO internal Id — passing the account number (AcctNum) returns `NoReportData` (empty).** This is the #1 trap and the reason a prior version appeared to return nothing.

| Account | account_id (use this) | AcctNum (do NOT use as id) |
|---|---|---|
| Brex Credit Card | 62 | 21140 |
| Amex Plat *12006 | 65 | 21120 |
| Amex Plat 2 *51005 | 67 | 21130 |
| Amex Centurion *01008 | 172 | 21150 |
