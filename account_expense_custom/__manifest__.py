# -*- coding: utf-8 -*-
{
    "name": "Account Expense Custom",
    "summary": "This module Adds functionality to manage Expenses based on Configuration.",
    "version": "12.0.7.3.3",
    "category": "Accounting",
    "license": "AGPL-3",
    "application": True,
    "installable": True,
    "depends": [
        'account_asset', 'purchase', 'account_accountant'
    ],
    "data": [
        "security/security_view.xml",
        "security/ir.model.access.csv",
        "views/account_expense_type_view.xml",
        "views/account_expense_transaction_view.xml",
        "views/product_view.xml",
        "views/invoice_view.xml",
        "wizard/generate_transaction_wizard_view.xml"
    ],
}
