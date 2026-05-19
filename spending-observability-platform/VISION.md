# Vision

## Why this exists

The goal is to answer three questions with evidence:

| Report | Definition |
|--------|------------|
| **Baseline burn** | What do I spend in a normal month? Ordinary recurring transactions only. |
| **Planning burn** | What should I budget for? Ordinary + annual spend ÷ 12 + irregular estimate ÷ 12. |
| **Cash outflow** | What actually left my accounts? Every debit, including one-offs. |

Before budgeting, the system must provide a reliable audit of real cash flow across accounts, cards, and currencies — with each transaction tagged by category and budget treatment so all three views can be computed.

## Product direction

This project is a local-first, transparent data pipeline for personal spending observability.

It is not a replacement for budget apps or full accounting systems.

## Design principles

### Local first

Data stays local by default. No cloud dependency required.

### Raw data is immutable

Source exports are preserved and re-processable.

### Exclusions are first-class

Transfers and other non-spend flows are explicitly marked, not mixed into spending.

### Explainable categorization

Rules should be visible and editable. Raw and normalized values should coexist.

### Human-in-the-loop for edge cases

The system surfaces what it cannot resolve automatically. A fast local web UI lets the human categorize quickly without leaving the terminal context.

## First milestone definition

Given raw CSV exports for a target month, produce an output that:

1. Separates true spending from non-spend transfers. ✅
2. Tags every transaction with a category and budget treatment. ⬜ (model in place; coverage and treatment assignment ongoing)
3. Displays a category-level summary web view with baseline, planning, and cash figures. ⬜

The pipeline and categorization queue are in place. The remaining gap is the summary web view that computes the three views above.
