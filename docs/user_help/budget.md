# Budget: bills, income, expenses, and reports

## What the Budget module tracks

Budget has seven tabs: Bills, Income Sources, Income, Expenses,
Summary, Trends, and Bank Sync. Bills and Income Sources are recurring
things you expect (a mortgage payment, a paycheck); Income and
Expenses are the actual entries as they happen.

## Bills and income sources

Add Bill and Add Income Source set up something recurring — a name,
amount, and due date/schedule. When one actually comes due, select it
and click Mark Paid (or Mark Received for income) — this both logs the
real transaction and updates the recurring record's next due date in
one action.

## Logging income and expenses directly

Add Income and Add Expense on their own tabs log a one-off entry
directly, without needing a recurring Bill/Income Source behind it —
useful for anything that isn't on a predictable schedule.

## Debts and payoff priority

The Debts tab tracks credit cards and loans (mortgages stay with Real
Estate): balance, interest rate, minimum payment, and any promotional
rate with its end date. Debts are ranked by what to pay off first. The
default "Hybrid" strategy pays the highest interest rate first, but
moves a debt to the front when its promo rate ends within 45 days.
Avalanche (highest rate first) and Snowball (smallest balance first)
are also available. Record Payment logs the payment as an expense and
lowers the balance. Cards, student loans, auto and personal loans and
lines of credit from connected banks appear automatically, marked
"(bank-synced)". The bank keeps their balance current (and a card's or
student loan's rate), but promo end dates are yours to enter. Banks
don't report an auto or personal loan's interest rate or minimum
payment, so add those yourself (the loan's note reminds you); until
then it ranks as if it were interest-free.

## Builds and tools (Builds & Tools tab)

See what your homestead builds and your tools really cost.

- **Builds** are your projects (the greenhouse, the fence, the coop).
  Give one a budget (Set Build Budget, or the Budget field when editing
  a project in Toolbox → Projects), then tag expenses to it. The tab
  shows spent vs. budget, what's left, and any overrun.
- **Tools and equipment** are the items on your Maintenance list. Give
  one a purchase price (edit it in Maintenance) or use **Record Tool
  Purchase**, which adds the tool and the expense together. Everything
  tagged to it afterwards (parts, repairs, fuel, oil changes) adds to
  its **total cost of ownership**. With engine-hour readings, you also
  see its **cost per hour**.
- **Tagging an expense:** Expenses → Add or Edit → "For build" and
  "For tool or equipment". Bank-synced expenses can be tagged the same
  way.
- Or just tell MIA: "I spent $240 on lumber for the greenhouse", "I
  bought a chainsaw for $329", "I changed the mower's oil, $35", "How
  much have I spent on the greenhouse?", "What has the mower cost me?"

## Business use of equipment (write-off records)

If you use personal equipment partly for business (the mower for
contract lawn care or your rentals), MIA keeps the record that backs up
the business share.

- **Log the business jobs:** Builds & Tools → **Log Business Use**, or
  tell MIA "I mowed the Maple duplex for 2 hours". If the job was for
  one of your rentals, it's credited to that rental's business.
- **Keep the hour meter current:** log engine-hour readings in
  Maintenance, at least at the start and end of the year. Total use
  comes from the meter; personal use is everything not logged as
  business.
- **See the worksheet:** Builds & Tools → **Business Use Worksheet**
  (export as PDF). It shows the business-use percentage, the business
  share of the year's running costs (split by business), the business
  share of the purchase price, the job log, and notes about anything
  weak in the record.

- **Vehicles, in miles:** for an item in the Vehicle category, Log
  Business Use asks for miles ("I drove 42 miles for the Johnson lawn
  job" works too), and total use comes from its odometer readings. The
  worksheet then also shows the **standard mileage** figure (business
  miles × the IRS rate) next to the actual-cost share. MIA doesn't guess
  the IRS rate: press **Set Mileage Rate…** in the worksheet and enter
  that year's rate from irs.gov once.
- **In the Business Report:** with "This Year" selected, the report has
  an "Equipment business use" section, each business's share of each
  item (hours or miles, business %, running costs, cost basis, standard
  mileage).

It's records and arithmetic from your own data, not tax advice. How to
depreciate the purchase, which method to use for a vehicle, and where
each amount goes on your return are for you or your tax preparer.

## Summary, Trends, and entities

The Summary tab totals everything for This Month/This Year/All Time,
including Budget Targets vs. actual spend per category. Trends charts
income vs. expenses over the last 12 months. If you've tagged entries
to a business entity (an LLC), Manage Entities… on the Summary tab is
where you add/edit them, and both Summary and the Business Report can
be filtered to just one.

## Bank Sync and reports

Bank Sync connects a real bank account (via Plaid) so its transactions
flow in automatically instead of manual entry — Connect a Bank… starts
that, Sync Now pulls the latest. Add Card/Loan Access… lets an already
connected bank feed its cards and loans into Debts. Disconnect
Selected… removes a connection on Plaid's side too (freeing one of your
connection slots), and Reset Plaid Setup… disconnects everything, for
example to switch from sandbox testing to your real accounts. Export Business Report (PDF)… and
Export Consolidated Report (All Entities)… on the Summary tab generate
a real PDF report for accountant/business use.

## Sorting bank charges to your businesses

Once you have at least one business (Summary tab → Manage Entities…),
MIA sorts synced bank charges to them. She learns from you: every charge
you tag to a business, or mark personal, teaches her where that store's
charges go. After a store has been sorted the same way three times, its
new charges are tagged automatically after each sync (the sync message
says how many). A charge for a rental property goes to the business that
owns the property.

Bank Sync → **Review Business Tags (N)** lists what's still waiting, with
MIA's guess preselected and why, plus what she tagged on her own so you
can correct it. "Decide later" leaves a charge for next time.

By voice: "which charges need a business?", "the Shell charge was for
lawn care", "the Walmart one was personal".
