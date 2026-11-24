---
id: K-0427
kind: debugging
title: An hourly that read batch builds low
status: confirmed
by: claude
created: 2026-11-24T15:32:21+00:00
concerns: core/hourly_earnings.py
from: commit:35aba92d
---
Review of 35aba92d: sales of a batch from stock (product.sell, record_sale) carry only a product_id, so a coasters job read $6 an hour, not $30. Now revenue with no job_id counts for the one job that made that product (several makers: the job counted apart, never split by guess); a job that used Materials has its Materials-category expenses left out (craft.cost defaults to Materials, so wood was counted twice); the person's words reach the tool (prompt_arg) and a day-job pay question (at my job, wage, paycheck, after taxes) is told it is the workshop's; and natural asks (builds make per hour, effective hourly) reach it.
