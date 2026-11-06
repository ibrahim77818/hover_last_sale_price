# Hover Last Sale Price (Odoo 17.0)

Show each customer's last sale prices right on the sales order line, and optionally pre-fill new lines
with the customer's last price, converted to the line's unit of measure and currency.

**Odoo 17.0** &middot; Community &amp; Enterprise &middot; English &amp; Arabic (`ar_001`, RTL) &middot; LGPL-3

## Branches

| Branch | Odoo version |
|---|---|
| [`16.0`](../../tree/16.0) | 16.0 |
| [`17.0`](../../tree/17.0) | 17.0 |
| [`18.0`](../../tree/18.0) | 18.0 |
| [`19.0`](../../tree/19.0) | 19.0 |

Use the branch that matches your Odoo version. This branch: **17.0**. Ported from 16.0: 17.0 settings layout (`<app>/<block>/<setting>`), `attrs` replaced by inline expressions, field registry descriptors, `usePopover(Component, options)` API, locked orders stay in the `sale` state.

## Features

- **Master switch** in *Sales &rsaquo; Configuration &rsaquo; Settings &rsaquo; Last Sale Price* (off by default, per company) with two independent options:
  - **Show Price History on Hover** with *Transactions to Show* (1&ndash;50, default 5).
  - **Suggest Last Sale Price** on new order lines.
- **Hover card** on the product of each order line and on a small history icon beside **Unit Price**:
  date, order, quantity, UoM, unit price and discount of the customer's most recent confirmed sales.
- **Normalization**: past prices in another unit of measure or currency are converted to the current line
  (shown as "&asymp; converted" in the card and used for the suggestion).
- **Whole customer**: history covers the company and all its contacts; drafts, cancelled orders and
  the order being edited are excluded.
- **Fast**: one indexed query, loaded in the background on hover, cached client-side for 30 seconds.
- **Arabic translation** with a right-to-left card.

## Installation

1. Clone the branch matching your Odoo version into a folder on your addons path:
   ```bash
   git clone -b 17.0 https://github.com/ibrahim77818/hover_last_sale_price.git
   ```
   The module is the `hover_last_sale_price/` folder inside the repository; add the repository folder to
   your `addons_path` (on Odoo.sh, add it as a submodule).
2. Update the Apps list and install **Hover Last Sale Price** (depends only on `sale`).
3. Enable it in *Sales &rsaquo; Configuration &rsaquo; Settings &rsaquo; Last Sale Price*.

## Tests

26 `TransactionCase` tests (tag `hover_last_sale_price`):

```bash
odoo-bin -d <db> -i hover_last_sale_price --test-tags hover_last_sale_price --stop-after-init
```

## Support

Author: **Ibrahim Yahia** &middot; [LinkedIn](https://www.linkedin.com/in/ibrahim-yahia) &middot; ibrahim.yahiah@gmail.com
&middot; License: LGPL-3
