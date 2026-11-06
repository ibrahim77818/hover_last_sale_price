/** @odoo-module **/

import { xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FloatField } from "@web/views/fields/float/float_field";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { useLastSalePriceHover } from "./last_sale_price_hover";

/**
 * Sales order line product field with the "last sale prices" hover card.
 * It extends the standard `sol_product_many2one` widget and is registered
 * under the same key, so it applies to whichever of product_id /
 * product_template_id is visible, and patches made by
 * sale_product_configurator / sale_product_matrix on the parent class keep
 * working (they live on the parent prototype).
 */
export class LastSalePriceProductField extends SaleOrderLineProductField {
    setup() {
        super.setup();
        this.lspHover = useLastSalePriceHover(() => this.props.record);
    }
}

// Wrap the parent template (resolved dynamically, so it follows whatever
// template name `sale` uses) in a hover zone with a small indicator icon.
LastSalePriceProductField.template = xml`
<div class="o_lsp_zone" t-on-mouseenter="lspHover.onMouseEnter" t-on-mouseleave="lspHover.onMouseLeave">
    <div class="o_lsp_field"><t t-call="${SaleOrderLineProductField.template}"/></div>
    <i t-if="lspHover.isActive" class="fa fa-history text-primary o_lsp_indicator" role="img"
       t-att-title="lspHover.indicatorTitle" t-att-aria-label="lspHover.indicatorTitle"/>
</div>`;

/**
 * Unit price field with a small history icon beside the price. Only the icon
 * opens the hover card, so editing the price is never obstructed.
 */
export class LastSalePriceUnitPriceField extends FloatField {
    setup() {
        super.setup();
        this.lspHover = useLastSalePriceHover(() => this.props.record);
    }
}

LastSalePriceUnitPriceField.template = xml`
<div class="o_lsp_zone o_lsp_price_zone">
    <i t-if="lspHover.isActive" class="fa fa-history text-primary o_lsp_indicator o_lsp_price_indicator"
       role="img" t-att-title="lspHover.indicatorTitle" t-att-aria-label="lspHover.indicatorTitle"
       t-on-mouseenter="lspHover.onMouseEnter" t-on-mouseleave="lspHover.onMouseLeave"/>
    <div class="o_lsp_field"><t t-call="${FloatField.template}"/></div>
</div>`;

registry
    .category("fields")
    .add("sol_product_many2one", LastSalePriceProductField, { force: true })
    .add("lsp_sol_product_many2one", LastSalePriceProductField)
    .add("lsp_price_unit", LastSalePriceUnitPriceField);
