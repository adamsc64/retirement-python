# Vision

## Why this exists

The goal is to answer a simple question with evidence: what am I actually spending?

Before budgeting, the system should provide a reliable audit of real cash flow across accounts, cards, and currencies.

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
2. Summarizes spending by category. ⬜
3. Lists unresolved transactions for manual review. ✅

The categorization pipeline and web queue are in place. The remaining gap is a printable/viewable monthly category summary.
