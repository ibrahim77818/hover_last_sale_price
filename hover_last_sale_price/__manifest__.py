# -*- coding: utf-8 -*-
{
    'name': 'Hover Last Sale Price',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': "Show each customer's last sale prices on hover and suggest "
               "the last price on new sales order lines",
    'description': """
Hover Last Sale Price
=====================
* Sales Settings master toggle (off by default) with two independent options:
  - Hover popup on sales order lines showing the last N confirmed sales of the
    product to the customer (date, order, quantity, UoM, unit price, discount).
  - Price suggestion: the unit price of a new line is filled with the
    customer's last sale price, normalized to the line's UoM and currency.
* History icon beside the product and beside the unit price on each line.
* Asynchronous OWL widget, silent RPC with client cache, no page blocking.
* History covers the whole commercial entity (company + its contacts).
* Multi-company aware, Arabic (ar_001) translation and RTL layout.
    """,
    'author': 'Ibrahim Yahia',
    'website': 'https://www.linkedin.com/in/ibrahim-yahia',
    'license': 'LGPL-3',
    'images': ['static/description/banner.png'],
    'depends': ['sale'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hover_last_sale_price/static/src/js/last_sale_price_popover.js',
            'hover_last_sale_price/static/src/js/last_sale_price_hover.js',
            'hover_last_sale_price/static/src/js/last_sale_price_field.js',
            'hover_last_sale_price/static/src/xml/last_sale_price_popover.xml',
            'hover_last_sale_price/static/src/scss/last_sale_price.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
