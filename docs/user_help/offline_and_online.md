# Working Offline and Online

## What works without the internet

Almost everything. MIA runs on this computer: her thinking (the
language model), listening and speaking, and every record and action
all work with no internet at all. That covers budget, debts, missions,
maintenance, notes, calendar, kitchen, workouts, people and pets. So do
reminders, alarms, daily briefings and suggestions, installed reference
packs, saved trail maps, map areas you've already viewed, calculators,
tools and backups. Your last synced bank balances stay visible too.

## What needs the internet

Only a few things:

- **Bank sync**: syncing bank, card and investment accounts, or
  connecting new ones. Offline, your last synced balances and every
  manual budget entry still work.
- **Phone notifications**: sending notifications to your phone. They
  still appear on this computer.
- **New map downloads**: map areas you haven't viewed before. Areas
  you've already viewed and saved trail maps still work.
- **Adding a trail map from a web link**: you can still add one from a
  file.
- **Talking to MIA from your phone away from home**: you can still talk
  to MIA on this computer.

## How MIA knows whether she's online

MIA quietly checks about once a minute whether the internet is
reachable. When it isn't, she knows. If you ask for something that needs
the internet, she'll say so, offer what she can do offline instead, and
offer to remind you once you're back online. Ask "are you online?" or
"what can you do without internet?" any time.

The check only opens a connection to a well-known internet address; no
data is sent. To turn it off, set `network.connectivity_check` to
`false` in `config/config.json`.
