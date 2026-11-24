---
id: K-0379
kind: test-procedure
title: Everyday money questions on the phone
status: confirmed
by: claude
created: 2026-11-24T07:36:05+00:00
concerns: core/question_plans.py, core/assistant_domain_actions.py, core/assistant_tools.py
from: commit:04b02e3a
---
A probe of twenty everyday money questions with no chat model found: what bills are due this week went to the week review (now NOT_FOR due/bills); how is my budget looking, what subscriptions am I paying for and spent $120 at the feed store reached nothing (budget gained budget, subscription(s), paying for; add_expense spent $); where should my tax refund go and where did my money go this month matched no plan by words (next dollar and money month words widened); will I have enough for rent went to coming up (now money_ahead's). Kept in tests/test_everyday_phrasing_routing.py.
