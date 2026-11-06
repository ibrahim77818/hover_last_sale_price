/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

/**
 * Card displayed by the popover service next to the hovered product.
 * Values arrive pre-formatted from the server (user language, currency
 * symbol position, decimal precision), so the template only lays them out.
 */
export class LastSalePricePopover extends Component {
    get footerText() {
        return sprintf(_t("Up to %s most recent confirmed sales"), this.props.data.limit);
    }

    onMouseEnter() {
        if (this.props.onMouseEnter) {
            this.props.onMouseEnter();
        }
    }

    onMouseLeave() {
        if (this.props.onMouseLeave) {
            this.props.onMouseLeave();
        }
    }
}
LastSalePricePopover.template = "hover_last_sale_price.LastSalePricePopover";
