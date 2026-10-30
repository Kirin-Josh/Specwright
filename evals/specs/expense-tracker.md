# Team Expenses — Product Brief

Synthetic spec written for Specwright evals. It deliberately has no requirement IDs.

## Background

Our consultants pay for travel and meals themselves and claim the money back by emailing
scanned receipts to the finance team. Claims get lost, approvals take weeks, and finance
re-types every amount into the accounting software. We want a small web app for claims.

## What people need to do

Consultants submit expense claims. A claim has one or more lines, and each line has a date,
a category (travel, meals, lodging or other), an amount with its currency, and a photo or PDF
of the receipt. Amounts in foreign currencies are converted to euros using the European
Central Bank rate of the expense date.

A consultant can save a claim as a draft and submit it later. Once submitted, a claim can no
longer be edited by the consultant unless it is sent back.

Each submitted claim goes to the consultant's manager, who approves it, rejects it with a
reason, or sends it back for changes. Claims above 1,000 euros also need a second approval
from the finance team after the manager.

Consultants get an email whenever one of their claims changes status.

Every Friday the finance team exports all approved claims of the week as a CSV file in the
format our accounting software imports, and those claims are then marked as paid.

## Rules and constraints

- Meal lines above 60 euros per person are flagged as over the policy limit so the approver
  sees it before deciding.
- Receipts are stored encrypted, and only the claimant, their manager and the finance team
  can see them.
- Everyone signs in with their Microsoft 365 work account.
- The app must work on a phone browser, because most receipts are photographed on the go.

## How we will know it works

- A consultant photographs two receipts on a phone, one of them in US dollars, submits the
  claim, and sees the dollar amount converted with the right day's rate.
- A 1,500 euro claim approved by the manager is not exported until finance approves it too.
- The Friday export opens in the accounting software without errors and every exported
  claim shows as paid.

## Later, not now

These ideas came up but are not part of this version: reading amounts from receipts
automatically with OCR, paying consultants directly by bank transfer from the app, and
corporate credit card integration.
