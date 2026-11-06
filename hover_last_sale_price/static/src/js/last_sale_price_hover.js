import { onWillUnmount, useEnv } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";
import { LastSalePricePopover } from "./last_sale_price_popover";

const OPEN_DELAY = 350; // ms of steady hover before fetching
const CLOSE_DELAY = 200; // ms grace period to move the mouse into the card
const CACHE_TTL = 30 * 1000; // ms a fetched history stays fresh
const CACHE_MAX_ENTRIES = 200;

/** Shared across all line widgets: one request per (customer, product, ...). */
const historyCache = new Map();

export function m2oId(value) {
    if (!value) {
        return false;
    }
    if (Array.isArray(value)) {
        return value[0] || false;
    }
    if (typeof value === "object") {
        return value.id || false;
    }
    return value;
}

/**
 * Hover controller shared by the order line widgets (product, unit price).
 * Must be called from a field component's setup(); `getRecord` returns the
 * current sale.order.line record.
 */
export function useLastSalePriceHover(getRecord) {
    // Raw (unprotected) ORM service: the request promise is shared through
    // the module cache, so it must still settle if this widget is destroyed
    // while the call is in flight. The ORM adds the user context itself.
    const orm = useEnv().services.orm;
    const state = {
        openTimer: null,
        closeTimer: null,
        requestId: 0,
        hovered: false,
    };
    // usePopover(Component, options) -> { open, close, isOpen }.
    const popover = usePopover(LastSalePricePopover, {
        position: "bottom",
        popoverClass: "o_lsp_popover_container",
        closeOnClickAway: true,
    });

    function rootRecord() {
        const model = getRecord().model;
        return model && model.root;
    }

    function isActive() {
        const root = rootRecord();
        const data = getRecord().data;
        return Boolean(
            root &&
                root.resModel === "sale.order" &&
                root.data.lsp_hover_enabled &&
                !data.display_type &&
                m2oId(data.product_id) &&
                m2oId(root.data.partner_id)
        );
    }

    function queryParams() {
        const root = rootRecord();
        const data = getRecord().data;
        const productId = m2oId(data.product_id);
        const partnerId = m2oId(root.data.partner_id);
        if (!productId || !partnerId) {
            return null;
        }
        return {
            product_id: productId,
            partner_id: partnerId,
            order_id: root.resId || false,
            company_id: m2oId(root.data.company_id),
            uom_id: m2oId(data.product_uom_id),
            currency_id: m2oId(root.data.currency_id),
        };
    }

    function fetchHistory(params) {
        const key = JSON.stringify(params);
        const cached = historyCache.get(key);
        if (cached && Date.now() - cached.time < CACHE_TTL) {
            return cached.promise;
        }
        if (historyCache.size >= CACHE_MAX_ENTRIES) {
            historyCache.clear();
        }
        const promise = orm.silent.call("sale.order.line", "lsp_get_history", [], params);
        historyCache.set(key, { time: Date.now(), promise });
        promise.catch(() => historyCache.delete(key));
        return promise;
    }

    function scheduleClose() {
        clearTimeout(state.closeTimer);
        state.closeTimer = setTimeout(() => {
            if (!state.hovered) {
                popover.close();
            }
        }, CLOSE_DELAY);
    }

    async function open(target) {
        const params = queryParams();
        if (!params) {
            return;
        }
        const requestId = ++state.requestId;
        let data;
        try {
            data = await fetchHistory(params);
        } catch {
            return; // access error / network: fail silently on hover
        }
        if (
            requestId !== state.requestId ||
            !state.hovered ||
            popover.isOpen ||
            !data ||
            !data.enabled ||
            !document.body.contains(target)
        ) {
            return;
        }
        popover.open(target, {
            data,
            onMouseEnter: () => {
                state.hovered = true;
                clearTimeout(state.closeTimer);
            },
            onMouseLeave: () => {
                state.hovered = false;
                scheduleClose();
            },
        });
    }

    function onMouseEnter(ev) {
        state.hovered = true;
        clearTimeout(state.closeTimer);
        if (popover.isOpen || !isActive()) {
            return;
        }
        const target = ev.currentTarget;
        // Do not get in the way of the user typing in an input of the cell.
        const active = document.activeElement;
        if (active && target.contains(active) && active.tagName === "INPUT") {
            return;
        }
        clearTimeout(state.openTimer);
        state.openTimer = setTimeout(() => open(target), OPEN_DELAY);
    }

    function onMouseLeave() {
        state.hovered = false;
        clearTimeout(state.openTimer);
        state.requestId++; // drop any in-flight response
        scheduleClose();
    }

    // usePopover closes its popover on unmount; only timers are left here.
    onWillUnmount(() => {
        clearTimeout(state.openTimer);
        clearTimeout(state.closeTimer);
        state.requestId++;
    });

    return {
        get isActive() {
            return isActive();
        },
        get indicatorTitle() {
            return _t("Hover to see the customer's last sale prices");
        },
        onMouseEnter,
        onMouseLeave,
    };
}
