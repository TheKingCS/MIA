---
id: K-0365
kind: debugging
title: A lump on the debts must keep a cleared debt minimum rolling
status: confirmed
by: claude
created: 2026-11-24T05:22:02+00:00
concerns: core/question_plans.py, core/canning_shelf.py
from: commit:d06b43c2, commit:95e4a2ae
---
An eighth fresh review found: question_plans.instead() took a one-off sum off the first debt and re-ran debt_math.simulate, which drops a zero-balance debt and its minimum from the monthly budget, so a bigger sum gave a later or unchanged debt-free date; the sum is now walked down the payoff order and the cleared debts minimums passed in as extra. buying() missed "get a $" (a trailing word boundary before $) and took "more months" or "afford to throw $1,000 at the card" the wrong way; its paying patterns are now anchored. canning_shelf matched sizes inside words (pinto, quartered) and stripped every of; food_of, size_of and count_of read on word boundaries and spoken counts. The safety line now lists NCHFP signs of spoiling and careful handling.
