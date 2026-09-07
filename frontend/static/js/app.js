console.log("Student Performance Assistant Loaded.");

// Auto-dismiss flash messages after a few seconds for a cleaner UI.
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach((el) => {
        setTimeout(() => {
            el.style.transition = "opacity 0.4s ease";
            el.style.opacity = "0";
        }, 4000);
    });
});

// Burger menu: toggle the slide-down navigation panel with keyboard support.
// While open, Tab/Shift+Tab cycle inside the panel (focus trap) and Escape
// closes it, returning focus to the toggle button.
document.addEventListener("DOMContentLoaded", () => {
    const nav = document.getElementById("siteNav");
    const toggle = document.getElementById("navToggle");
    const menu = document.getElementById("navMenu");
    if (!nav || !toggle || !menu) return;

    const FOCUSABLE =
        'a[href], button:not([disabled]), input:not([disabled]), select, textarea, ' +
        '[tabindex]:not([tabindex="-1"])';

    // Keep collapsed menu items out of the tab order even during the
    // slide-down/up transition (visibility only kicks in after the delay).
    menu.inert = true;

    let lastFocus = null;

    function focusableItems() {
        return Array.from(menu.querySelectorAll(FOCUSABLE)).filter(
            (el) => el.getClientRects().length > 0
        );
    }

    function openMenu() {
        if (nav.classList.contains("open")) return;
        lastFocus = document.activeElement;
        menu.inert = false;
        nav.classList.add("open");
        toggle.setAttribute("aria-expanded", "true");
        const items = focusableItems();
        if (items.length > 0) {
            items[0].focus();
        } else {
            toggle.focus();
        }
    }

    function closeMenu(restoreFocus) {
        if (!nav.classList.contains("open")) return;
        nav.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        menu.inert = true;
        if (restoreFocus) {
            if (lastFocus && typeof lastFocus.focus === "function") {
                lastFocus.focus();
            } else {
                toggle.focus();
            }
        }
        lastFocus = null;
    }

    toggle.addEventListener("click", () => {
        if (nav.classList.contains("open")) {
            closeMenu(false); // focus already sits on the toggle
        } else {
            openMenu();
        }
    });

    // Keyboard navigation inside the open panel:
    //   - Tab / Shift+Tab cycle through the items (focus trap, no leaks)
    //   - ArrowDown / ArrowUp / Home / End move through the links
    menu.addEventListener("keydown", (event) => {
        if (!nav.classList.contains("open")) return;
        const items = focusableItems();
        if (items.length === 0) return;

        const first = items[0];
        const last = items[items.length - 1];
        const current = document.activeElement;

        if (event.key === "Tab") {
            if (
                (event.shiftKey && (current === first || current === menu || current === toggle)) ||
                (!event.shiftKey && (current === last || current === menu || current === toggle))
            ) {
                event.preventDefault();
                (event.shiftKey ? last : first).focus();
            }
        } else if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            const index = items.indexOf(current);
            if (index === -1) return;
            event.preventDefault();
            const step = event.key === "ArrowDown" ? 1 : -1;
            items[(index + step + items.length) % items.length].focus();
        } else if (event.key === "Home") {
            event.preventDefault();
            first.focus();
        } else if (event.key === "End") {
            event.preventDefault();
            last.focus();
        }
    });

    // Close after choosing a link (navigation will move focus to the new page).
    menu.querySelectorAll("a").forEach((link) => {
        link.addEventListener("click", () => closeMenu(false));
    });

    // Close when clicking anywhere outside the menu, without stealing focus
    // from whatever the user clicked.
    document.addEventListener("click", (event) => {
        if (!nav.contains(event.target)) closeMenu(false);
    });

    // Close on Escape and hand focus back to the toggle button.
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") closeMenu(true);
    });
});
