---
id: K-0410
kind: implementation
title: Quotes out say what their dates mean
status: confirmed
by: claude
created: 2026-11-24T12:45:39+00:00
concerns: core/assistant_business_voice_actions.py
from: commit:b833127e
---
list_quotes now notes each quote's dates (_age_note): expired or within three days of its good-until date, or sent a week ago (FOLLOW_UP_DAYS, from created_at: a quote keeps no sent date) with no answer, worth a follow-up, the ones to call named last; a draft is never chased. It hears which quotes should I follow up on and haven't heard back.
