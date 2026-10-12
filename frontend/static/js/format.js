/* ---------------------------------------------------------------------------
 * Display rounding — the browser twin of backend/services/rounding.py (|r2).
 *
 * Every number shown in the UI goes through fmt2(): chart labels, tooltips,
 * sliders, live summaries. Calculations keep full precision; only what the
 * lecturer sees is rounded, so the two sides can never drift apart.
 *
 * Rules (kept identical to the Python helper):
 *   - at most 2 decimal places, rounded half-up (0.005 -> 0.01);
 *   - whole numbers stay bare (70, not 70.00) and trailing zeros are trimmed;
 *   - null / undefined / NaN / Infinity show as an em dash;
 *   - -0.00 is never shown — anything that rounds to zero is "0".
 * ------------------------------------------------------------------------- */
(function (global) {
    'use strict';

    var DASH = '\u2014'; // em dash, same as Python's rounding.DASH

    /**
     * Round for display: at most 2 decimals, half-up, dash for missing values.
     * @param {number|string|null|undefined} value
     * @param {string} [dash] text to use when there is nothing to show
     * @returns {string}
     */
    function fmt2(value, dash) {
        var empty = dash === undefined ? DASH : dash;
        if (value === null || value === undefined || value === '') return empty;
        var number = typeof value === 'number' ? value : Number(value);
        if (typeof number !== 'number' || !isFinite(number)) return empty;

        // Half-up at the hundredth. The EPSILON nudge is the standard trick that
        // stops binary floats dragging a .005 case downwards the way
        // Math.round(2.675 * 100) does; the Python helper uses Decimal half-up.
        var sign = number < 0 ? '-' : '';
        var rounded = Math.round((Math.abs(number) + Number.EPSILON) * 100) / 100;
        if (rounded === 0) return '0'; // also collapses -0.0 and tiny negatives
        var text = rounded.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
        return sign + text;
    }

    /**
     * Same rounding but with a trailing percent sign, for labels and tooltips.
     */
    function fmt2pct(value, dash) {
        var text = fmt2(value, dash);
        return text === (dash === undefined ? DASH : dash) ? text : text + '%';
    }

    global.fmt2 = fmt2;
    global.fmt2pct = fmt2pct;
})(window);
