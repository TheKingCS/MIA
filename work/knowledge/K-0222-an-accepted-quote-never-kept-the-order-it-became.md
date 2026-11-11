---
id: K-0222
kind: debugging
title: An accepted quote never kept the order it became
status: confirmed
by: claude
created: 2026-11-11T08:27:49+00:00
concerns: core/business_book.py, core/business_actions.py
from: dec:DEC-0153, file:core/business_book.py, file:tests/test_web_businesses.py
---
Found writing the Businesses tests (2026-11-11). quote.accept made the order and then called BusinessBook.update_quote(status='Accepted', order_id=...), but _set refuses any *_id field it doesn't allow, and it refused order_id after it had already set the status. The quote showed Accepted and the order existed, but the quote's order_id stayed empty and the action raised halfway. tests/test_business.py didn't look at the quote's order_id, so it passed. Fixed in update_quote: order_id is taken out of the fields and set after the rest (only accepting sets it; the edit form never offers it). Lesson: a setter that validates field by field can half-apply a change; check the whole set before setting any.
