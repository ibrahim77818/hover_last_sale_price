import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

/**
 * Card displayed by the popover service next to the hovered cell.
 * Values arrive pre-formatted from the server (user language, currency
 * symbol position, decimal precision), so the template only lays them out.
 * The popover hook also passes a `close` prop.
 */
export class LastSalePricePopover extends Component {
    static template = "hover_last_sale_price.LastSalePricePopover";
    // No static props on purpose: the popover hook hands props over
    // through a prototype chain (Object.create) and adds `close`, which
    // strict props validation in debug mode could reject.

    get footerText() {
        return _t("Up to %s most recent confirmed sales", this.props.data.limit);
    }

    onMouseEnter() {
        this.props.onMouseEnter?.();
    }

    onMouseLeave() {
        this.props.onMouseLeave?.();
    }
}
