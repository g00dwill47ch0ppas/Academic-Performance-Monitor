/**
 * Guided tutorial + first-run welcome for the Student Performance Assistant.
 *
 * Loaded from base.html on every page, because the tour walks across pages:
 * sessionStorage keeps the active flag and the current step index, so the tour
 * resumes on the next page after a navigation.
 *
 * Everything the tour needs is data: the STEPS array below. Each step is
 *   {
 *     route:    page the step lives on ("/" or "/student/*")
 *     selector: CSS selector of the element to highlight (null = centred recap)
 *     action:   "click" | "type" | "select" | "submit" | "next"
 *               (how the step advances — "next" means the Next button)
 *     title, text          what the tour says
 *     hint                 shown while waiting for the user to act
 *     missing              shown when the selector is not on the page
 *     fill                 example value for the "Fill an example for me" helper
 *     inMenu               true when the target lives in the navigation panel
 *   }
 *
 * The tour is presentation only: it never submits data on the user's behalf
 * (except the module it is told to create) and it never invents or requests
 * real student data.
 */
(function () {
    "use strict";

    var KEYS = {
        active: "dss_tutorial_active",
        step: "dss_tutorial_step",
        section: "dss_tutorial_section",
        seen: "dss_tutorial_seen"
    };

    /**
     * The tour is split into parts so nobody has to sit through all 30 steps.
     * Each step declares a `section`; the parts below give it a title and a blurb,
     * and the step range of a part is derived from the steps themselves — so the
     * chooser can never drift away from the steps it describes.
     */
    var SECTIONS = [
        {
            id: "modules",
            title: "Create a module",
            blurb:
                "Open the menu, then create your own module — code, name and pass threshold " +
                "— and switch back to the sample class."
        },
        {
            id: "plan",
            title: "Assessment plan",
            blurb:
                "Add assessments to the plan and set the weights that make up the " +
                "participation mark."
        },
        {
            id: "students",
            title: "Students & marks",
            blurb:
                "Add a student with an anonymised code, enter marks, and capture a whole " +
                "class in one pass."
        },
        {
            id: "results",
            title: "Results & at-risk",
            blurb:
                "Read the dashboard indicators and the at-risk list, and see what the " +
                "min/max bounds mean."
        },
        {
            id: "cohort",
            title: "Cohort planning",
            blurb:
                "Set a target and a weight range for every assessment, run the optimiser " +
                "and read its result."
        }
    ];

    var STEPS = [
        {
            route: "/",
            selector: "#navToggle",
            action: "click",
            section: "modules",
            title: "Open the navigation panel",
            text:
                "This button opens the app menu. The panel lists every page for the module " +
                "you are working in, and the module switcher at the bottom moves you between " +
                "modules.",
            hint: "Click the menu button (top right) to continue."
        },
        {
            route: "/",
            selector: "#navSidebar",
            action: "next",
            section: "modules",
            title: "Your pages and your modules",
            text:
                "The top of the panel is the page list — Overview, At-risk students, Students, " +
                "Enter marks, Assessment plan, Cohort planning, Settings and Tutorial. Below it " +
                "is the module switcher: each module keeps its own plan, students and pass " +
                "threshold, so switching never mixes their data."
        },
        {
            route: "/",
            selector: "#navSidebar a[href='/modules']",
            action: "click",
            section: "modules",
            inMenu: true,
            title: "Start by creating a module",
            text:
                "Open Modules to create a module for your own subject, or to import one from a " +
                "CSV/XLSX file.",
            hint: "Click Modules in the panel."
        },
        {
            route: "/modules",
            selector: "#module_code",
            action: "type",
            section: "modules",
            fill: "DEMO101",
            title: "Type a module code",
            text:
                "The code is the short identifier for the module (for example CS101). It must " +
                "be unique.",
            hint: "Type a code — or use “Fill an example for me”."
        },
        {
            route: "/modules",
            selector: "#module_name",
            action: "type",
            section: "modules",
            fill: "Tutorial demo module",
            title: "Give the module a name",
            text: "A readable name such as “Calculus 1”. It only shows up in labels.",
            hint: "Type a name — or use “Fill an example for me”."
        },
        {
            route: "/modules",
            selector: "#module_threshold",
            action: "type",
            section: "modules",
            fill: "50",
            title: "Set the pass threshold",
            text:
                "The pass threshold decides the at-risk flags: any student whose best-case " +
                "participation mark cannot reach this percentage needs attention. You can change " +
                "it later on the Settings page.",
            hint: "Type a threshold (for example 50) — or use “Fill an example for me”."
        },
        {
            route: "/modules",
            selector: "#create-module-submit",
            action: "click",
            section: "modules",
            title: "Create the module",
            text:
                "This creates the module, makes it the active one, and takes you to its " +
                "dashboard — which is still empty, because it has no assessment plan or " +
                "students yet.",
            hint: "Click Create module."
        },
        {
            route: "/",
            selector: "#navToggle",
            action: "click",
            section: "modules",
            title: "Switch back to the sample module",
            text:
                "Your module is now active. Open the menu once more and choose the bundled " +
                "sample module (CS101) so the rest of the tour has a full class to work with.",
            hint: "Click the menu button to continue."
        },
        {
            route: "/",
            selector: "#navSidebar a[href$='/modules/CS101/activate']",
            action: "click",
            section: "modules",
            inMenu: true,
            title: "Pick the sample module",
            text:
                "CS101 (Sample module) ships with 15 anonymised students, six assessments and " +
                "the pass threshold already set. It is simulated data and resets when the app " +
                "restarts.",
            missing:
                "CS101 is not in the switcher right now — open Modules and choose the sample " +
                "module, then carry on here.",
            hint: "Click CS101 in the panel."
        },
        {
            route: "/",
            selector: "#navSidebar a[href='/plan']",
            action: "click",
            section: "modules",
            inMenu: true,
            title: "Define the assessment plan",
            text:
                "Every module has an assessment plan: the list of assessments that make up the " +
                "participation mark, each with a weight.",
            hint: "Click Assessment plan in the panel."
        },
        {
            route: "/plan",
            selector: "#assessment_name",
            action: "type",
            section: "plan",
            fill: "Tutorial Test",
            title: "Name an assessment",
            text:
                "Type what the assessment is called, for example “Class Test 1” or " +
                "“Practical 3”. Names must be unique inside the module.",
            hint: "Type a name — or use “Fill an example for me”."
        },
        {
            route: "/plan",
            selector: "#weight",
            action: "type",
            section: "plan",
            fill: "10",
            title: "Set its weight",
            text:
                "The weight is the share of the final participation mark, in percent. The " +
                "weights in a plan should add up to 100% — the badge at the top of this page " +
                "keeps the running total.",
            hint: "Type a weight (for example 10) — or use “Fill an example for me”."
        },
        {
            route: "/plan",
            selector: "#add-assessment-submit",
            action: "next",
            section: "plan",
            title: "Add it to the plan",
            text:
                "Clicking Add to plan commits the assessment and gives every existing student a " +
                "blank “not yet written” entry for it. The tour leaves the sample plan as it is, " +
                "so you can try the button yourself afterwards."
        },
        {
            route: "/plan",
            selector: "#navSidebar a[href='/students']",
            action: "click",
            section: "plan",
            inMenu: true,
            title: "Now the students",
            text: "Open Students to see the cohort, and to add or edit students.",
            hint: "Click Students in the panel."
        },
        {
            route: "/students",
            selector: "a[href$='/students/new']",
            action: "click",
            section: "students",
            title: "Add a student",
            text:
                "This opens the student form. Each student is identified by an anonymised code — " +
                "never a real name, student number or e-mail address.",
            missing:
                "This module has no students yet. That is fine to see, but the tour continues " +
                "more usefully on the sample module — switch back to CS101 when you like.",
            hint: "Click Add student."
        },
        {
            route: "/students/new",
            selector: "#student_code",
            action: "type",
            section: "students",
            fill: "STU900",
            title: "Type an anonymised code",
            text:
                "A code such as STU016 or 46997245 keeps the record anonymous, which the " +
                "study's ethics clearance requires. That is the only identifying field.",
            hint: "Type a code — or use “Fill an example for me”."
        },
        {
            route: "/students/new",
            selector: "input[name='mark_0']",
            action: "type",
            section: "students",
            fill: "65",
            title: "Enter the marks",
            text:
                "One mark per assessment, out of 100. Leave a field blank when the class has " +
                "not written that assessment yet — the app then works out the best and worst " +
                "participation mark still reachable. The weight next to each name comes from " +
                "the assessment plan.",
            missing:
                "This module has no assessment plan yet, so there are no mark fields here. " +
                "Define the plan first, then come back.",
            hint: "Type a mark (for example 65) — or use “Fill an example for me”."
        },
        {
            route: "/students/new",
            selector: "#navSidebar a[href='/marks']",
            action: "click",
            section: "students",
            inMenu: true,
            title: "Entering marks for the whole class",
            text:
                "When a class writes an assessment, Enter marks captures the entire cohort in " +
                "one pass instead of opening each student.",
            hint: "Click Enter marks in the panel."
        },
        {
            route: "/marks",
            selector: "#assessment",
            action: "select",
            section: "students",
            title: "Choose the assessment",
            text:
                "Pick the assessment from this list. The table then shows every student with " +
                "their mark and the previous value, so you can see what you are overwriting.",
            hint: "Choose an assessment other than the current one."
        },
        {
            route: "/marks",
            selector: "input[name^='mark_']",
            action: "type",
            section: "students",
            fill: "70",
            title: "Record a mark",
            text:
                "Type each student's mark and save the page. A blank stays “not yet written”. " +
                "These marks drive the participation mark, the at-risk bounds and cohort " +
                "planning.",
            hint: "Type a mark (for example 70) — or use “Fill an example for me”."
        },
        {
            route: "/marks",
            selector: "#navSidebar a[href='/']",
            action: "click",
            section: "students",
            inMenu: true,
            title: "Back to the dashboard",
            text:
                "The dashboard summarises the class: the average participation mark, how many " +
                "students are at-risk, and the class size. The cards themselves are clickable.",
            hint: "Click Overview in the panel."
        },
        {
            route: "/",
            selector: ".card-row",
            action: "next",
            section: "results",
            title: "Reading the indicators",
            text:
                "Class average is the mean participation mark across the cohort. At-risk " +
                "students counts those who cannot clear the pass threshold even with full marks " +
                "on everything still to be written — open it for the list. Class size is the " +
                "number of students in the module. The min/max bounds you will see on student " +
                "pages are what the at-risk flag is built from."
        },
        {
            route: "/",
            selector: ".panel .row-actions a[href='/at-risk']",
            action: "click",
            section: "results",
            title: "Check who needs attention",
            text: "This quick action opens the at-risk list — the students to act on first.",
            hint: "Click Review at-risk students."
        },
        {
            route: "/at-risk",
            selector: "main .panel",
            action: "next",
            section: "results",
            title: "What “at-risk” means",
            text:
                "A student is flagged when even their best-case participation mark stays below " +
                "the module's pass threshold. Each row shows the current mark and the best/worst " +
                "case still reachable; View opens the student's page, including the " +
                "participation plan that lists the marks they need on the assessments left.",
            missing:
                "No student is flagged in this module at the moment — good news. The same page " +
                "explains the rule, and the sample module has more to look at."
        },
        {
            route: "/at-risk",
            selector: "#navSidebar a[href='/cohort']",
            action: "click",
            section: "results",
            inMenu: true,
            title: "Plan the assessment weights",
            text:
                "Cohort planning is where the model searches for a different spread of weights. " +
                "It is a what-if tool: it shows what the plan could look like, and nothing " +
                "changes until you edit the plan yourself.",
            hint: "Click Cohort planning in the panel."
        },
        {
            route: "/cohort",
            selector: "#target_average",
            action: "select",
            section: "cohort",
            title: "Choose a target",
            text:
                "Set the class average you would like to reach. The optimiser looks for the " +
                "weight combination that gets the class closest to it.",
            hint: "Move the slider to continue."
        },
        {
            route: "/cohort",
            selector: "input[data-role='min-number']",
            action: "type",
            section: "cohort",
            fill: "5",
            title: "Constrain every weight",
            text:
                "Each assessment gets a minimum and a maximum weight — those ranges are the " +
                "constraints of the optimisation. A weight can never be zero: the solver keeps " +
                "a 1% floor, so minimums must stay above 0%. The page adds the minimums and " +
                "maximums up live, because the minimums may not exceed 100% and the maximums " +
                "may not fall below 100%.",
            missing:
                "This module has no assessments or no students yet, so there are no ranges to " +
                "set. Switch to the sample module to see them.",
            hint: "Type a minimum (for example 5) — or use “Fill an example for me”."
        },
        {
            route: "/cohort",
            selector: "#cohortCalculate",
            action: "click",
            section: "cohort",
            title: "Run the optimisation",
            text:
                "Calculate weights solves Algorithm 3 and reports its status — optimal, " +
                "infeasible, or did not converge — along with how close the class gets to your " +
                "target.",
            hint: "Click Calculate weights."
        },
        {
            route: "/cohort",
            selector: ".status-banner",
            action: "next",
            section: "cohort",
            title: "Read the result",
            text:
                "The banner says whether the target was reached, and if not, by how much it was " +
                "missed. The table and the bars compare every proposed weight with the range you " +
                "allowed, and the cards above show the resulting class average and the distance " +
                "from your target."
        },
        {
            route: "/cohort",
            selector: null,
            action: "next",
            section: "cohort",
            title: "That is the whole workflow",
            text:
                "Create a module → define the assessment plan → add students and marks → watch " +
                "the dashboard and the at-risk list → plan the cohort's weights. You can replay " +
                "this tour any time from the menu (Tutorial), and the question-mark button on " +
                "any page explains that page. All data is simulated and lives in memory, so it " +
                "resets when the app restarts — never enter real student data."
        }
    ];

    // ---------------------------------------------------------------------- //
    // Storage + small helpers
    // ---------------------------------------------------------------------- //
    function read(store, key) {
        try {
            return window[store].getItem(key);
        } catch (e) {
            return null;
        }
    }

    function write(store, key, value) {
        try {
            window[store].setItem(key, value);
        } catch (e) {
            /* private mode or storage disabled — the tour just will not persist */
        }
    }

    function remove(store, key) {
        try {
            window[store].removeItem(key);
        } catch (e) {
            /* ignore */
        }
    }

    function pathname() {
        return window.location.pathname.replace(/\/+$/, "") || "/";
    }

    /** Match a step route ("/" or "/student/*") against the current path. */
    function routeMatches(pattern, path) {
        var escaped = pattern.split("*").map(function (part) {
            return part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        });
        return new RegExp("^" + escaped.join(".*") + "$").test(path);
    }

    // ---------------------------------------------------------------------- //
    // Tour state + DOM
    // ---------------------------------------------------------------------- //
    var tour = {
        active: false,
        index: 0,
        // Step range currently being run: the whole tour, or one section of it.
        range: { first: 0, last: STEPS.length - 1, label: "" },
        step: null,
        target: null,
        root: null,
        callout: null,
        highlight: null,
        arrow: null,
        dims: {},
        size: { w: 0, h: 0 },
        signature: "",
        rafId: 0,
        timer: 0,
        menuTimer: 0,
        offRoute: false
    };

    var els = {};

    function ensureRoot() {
        if (tour.root) return tour.root;

        var root = document.createElement("div");
        root.className = "tour-root";
        root.setAttribute("data-tour-root", "");
        root.innerHTML = [
            '<div class="tour-dim" data-dim="top"></div>',
            '<div class="tour-dim" data-dim="bottom"></div>',
            '<div class="tour-dim" data-dim="left"></div>',
            '<div class="tour-dim" data-dim="right"></div>',
            '<div class="tour-highlight" hidden></div>',
            '<div class="tour-callout" role="dialog" aria-labelledby="tourStepTitle"',
            '     aria-describedby="tourStepText" tabindex="-1">',
            '  <span class="tour-arrow" data-side="top"></span>',
            '  <div class="tour-head">',
            '    <span class="tour-progress" id="tourProgress"></span>',
            '    <button type="button" class="tour-exit" data-tour="exit">Exit tutorial</button>',
            "  </div>",
            '  <h3 class="tour-title" id="tourStepTitle"></h3>',
            '  <p class="tour-text" id="tourStepText"></p>',
            '  <p class="tour-hint" id="tourHint" hidden></p>',
            '  <div class="tour-actions">',
            '    <button type="button" class="tour-btn" data-tour="back">Back</button>',
            '    <button type="button" class="tour-btn tour-next" data-tour="next">Next</button>',
            '    <button type="button" class="tour-btn" data-tour="fill" hidden>Fill an example for me</button>',
            '    <button type="button" class="tour-btn" data-tour="skip">Skip step</button>',
            "  </div>",
            '  <p class="tour-data-note">Simulated data only — everything is in memory and ',
            "     resets when the app restarts.</p>",
            "</div>",
            '<div class="tour-live" role="status" aria-live="polite"></div>'
        ].join("\n");

        document.body.appendChild(root);

        tour.root = root;
        tour.callout = root.querySelector(".tour-callout");
        tour.highlight = root.querySelector(".tour-highlight");
        tour.arrow = root.querySelector(".tour-arrow");
        els.progress = root.querySelector(".tour-progress");
        els.title = root.querySelector(".tour-title");
        els.text = root.querySelector(".tour-text");
        els.hint = root.querySelector(".tour-hint");
        els.next = root.querySelector('[data-tour="next"]');
        els.back = root.querySelector('[data-tour="back"]');
        els.skip = root.querySelector('[data-tour="skip"]');
        els.fill = root.querySelector('[data-tour="fill"]');
        els.exit = root.querySelector('[data-tour="exit"]');
        els.live = root.querySelector(".tour-live");
        els.dims = {
            top: root.querySelector('[data-dim="top"]'),
            bottom: root.querySelector('[data-dim="bottom"]'),
            left: root.querySelector('[data-dim="left"]'),
            right: root.querySelector('[data-dim="right"]')
        };

        root.addEventListener("click", function (event) {
            var role = event.target.closest ? event.target.closest("[data-tour]") : null;
            if (!role) return;
            event.preventDefault();
            var action = role.getAttribute("data-tour");
            if (action === "next" || action === "skip") advance();
            else if (action === "back") goBack();
            else if (action === "fill") fillExample();
            else if (action === "exit") exitTour(true);
        });

        return root;
    }

    /** First and last step index of a section, derived from the steps themselves. */
    function sectionRange(sectionId) {
        var range = null;
        STEPS.forEach(function (step, index) {
            if (step.section !== sectionId) return;
            if (!range) range = { first: index, last: index };
            else range.last = index;
        });
        return range;
    }

    function findSection(sectionId) {
        for (var i = 0; i < SECTIONS.length; i++) {
            if (SECTIONS[i].id === sectionId) return SECTIONS[i];
        }
        return null;
    }

    /** Range for a section id, or the whole tour when the id is empty/unknown. */
    function rangeFor(sectionId) {
        var whole = { first: 0, last: STEPS.length - 1, label: "", section: "" };
        if (!sectionId) return whole;
        var section = findSection(sectionId);
        var range = section ? sectionRange(sectionId) : null;
        if (!section || !range) return whole;
        return { first: range.first, last: range.last, label: section.title, section: sectionId };
    }

    function menuOpen() {
        var sidebar = document.getElementById("navSidebar");
        return !!(sidebar && sidebar.classList.contains("active"));
    }

    function setMenu(open) {
        var toggle = document.getElementById("navToggle");
        if (!toggle || menuOpen() === open) return false;
        toggle.click();
        return true;
    }

    function toast(message) {
        var el = document.createElement("div");
        el.className = "tour-toast";
        el.setAttribute("role", "status");
        el.textContent = message;
        document.body.appendChild(el);
        window.setTimeout(function () {
            el.remove();
        }, 7000);
    }

    /** Keep the highlighted hole and the callout glued to the target element. */
    function place(el, left, top, width, height) {
        el.style.left = Math.round(left) + "px";
        el.style.top = Math.round(top) + "px";
        el.style.width = Math.max(0, Math.round(width)) + "px";
        el.style.height = Math.max(0, Math.round(height)) + "px";
    }

    function setDims(rect) {
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var pad = 6;

        if (!rect) {
            place(els.dims.top, 0, 0, vw, vh);
            place(els.dims.bottom, 0, 0, 0, 0);
            place(els.dims.left, 0, 0, 0, 0);
            place(els.dims.right, 0, 0, 0, 0);
            return;
        }

        var x = rect.left - pad;
        var y = rect.top - pad;
        var w = rect.width + pad * 2;
        var h = rect.height + pad * 2;

        place(els.dims.top, 0, 0, vw, Math.max(0, y));
        place(els.dims.bottom, 0, y + h, vw, Math.max(0, vh - (y + h)));
        place(els.dims.left, 0, y, Math.max(0, x), h);
        place(els.dims.right, x + w, y, Math.max(0, vw - (x + w)), h);
    }

    function measureCallout() {
        tour.callout.style.visibility = "hidden";
        tour.size = { w: tour.callout.offsetWidth, h: tour.callout.offsetHeight };
        tour.callout.style.visibility = "";
    }

    function placeCallout(rect) {
        var vw = window.innerWidth;
        var vh = window.innerHeight;
        var cw = tour.size.w;
        var ch = tour.size.h;
        var gap = 16;

        if (!rect) {
            place(tour.callout, (vw - cw) / 2, (vh - ch) / 2, cw, ch);
            tour.arrow.hidden = true;
            return;
        }

        var space = {
            bottom: vh - rect.bottom - gap,
            top: rect.top - gap,
            right: vw - rect.right - gap,
            left: rect.left - gap
        };
        var order = ["bottom", "top", "right", "left"];
        var side = null;
        for (var i = 0; i < order.length; i++) {
            var candidate = order[i];
            var needed = candidate === "bottom" || candidate === "top" ? ch : cw;
            if (space[candidate] >= needed + 8) {
                side = candidate;
                break;
            }
        }
        if (!side) {
            side = order.reduce(function (best, candidate) {
                return space[candidate] > space[best] ? candidate : best;
            }, "bottom");
        }

        var left;
        var top;
        if (side === "bottom" || side === "top") {
            left = rect.left + rect.width / 2 - cw / 2;
            top = side === "bottom" ? rect.bottom + gap : rect.top - gap - ch;
        } else {
            top = rect.top + rect.height / 2 - ch / 2;
            left = side === "right" ? rect.right + gap : rect.left - gap - cw;
        }
        left = Math.min(Math.max(8, left), Math.max(8, vw - cw - 8));
        top = Math.min(Math.max(8, top), Math.max(8, vh - ch - 8));

        tour.callout.style.left = Math.round(left) + "px";
        tour.callout.style.top = Math.round(top) + "px";

        // Arrow sits on the callout edge that faces the element.
        var edge =
            side === "bottom" ? "top" : side === "top" ? "bottom" : side === "right" ? "left" : "right";
        tour.arrow.hidden = false;
        tour.arrow.setAttribute("data-side", edge);
        if (edge === "top" || edge === "bottom") {
            var x = Math.min(Math.max(16, rect.left + rect.width / 2 - left - 6), Math.max(16, cw - 30));
            tour.arrow.style.left = Math.round(x) + "px";
            tour.arrow.style.top = "";
        } else {
            var y = Math.min(Math.max(16, rect.top + rect.height / 2 - top - 6), Math.max(16, ch - 30));
            tour.arrow.style.top = Math.round(y) + "px";
            tour.arrow.style.left = "";
        }
    }

    function reposition() {
        var rect = tour.target ? tour.target.getBoundingClientRect() : null;
        tour.highlight.hidden = !rect;
        setDims(rect);
        if (rect) place(tour.highlight, rect.left - 6, rect.top - 6, rect.width + 12, rect.height + 12);
        placeCallout(rect);
    }

    function followTarget() {
        if (!tour.active) return;
        var rect = tour.target ? tour.target.getBoundingClientRect() : null;
        var signature = rect
            ? [rect.top, rect.left, rect.width, rect.height, window.innerWidth, window.innerHeight]
                  .map(Math.round)
                  .join(",")
            : "none:" + window.innerWidth + "x" + window.innerHeight;
        if (signature !== tour.signature) {
            tour.signature = signature;
            reposition();
        }
        tour.rafId = window.requestAnimationFrame(followTarget);
    }

    function announce() {
        if (!els.live || !tour.step) return;
        var total = tour.range.last - tour.range.first + 1;
        var position = tour.index - tour.range.first + 1;
        els.live.textContent =
            "Step " + position + " of " + total +
            (tour.range.label ? " · " + tour.range.label : "") + ". " +
            tour.step.title + ". " + tour.step.text;
    }

    function renderStep(step, offRoute) {
        var target = !step.selector || offRoute ? null : document.querySelector(step.selector);
        tour.target = target;
        tour.offRoute = !!offRoute;

        var total = tour.range.last - tour.range.first + 1;
        var position = tour.index - tour.range.first + 1;
        els.progress.textContent =
            "Step " + position + " of " + total + (tour.range.label ? " · " + tour.range.label : "");
        els.title.textContent = step.title;
        els.text.textContent = step.text;

        var hint = "";
        if (offRoute) {
            hint =
                "This step happens on another page (“" + step.route + "”). " +
                "Use “Next” to be taken there.";
        } else if (!target) {
            hint = step.missing || "";
        } else if (step.hint) {
            hint = step.hint;
        }
        els.hint.textContent = hint;
        els.hint.hidden = !hint;

        els.fill.hidden = !(step.fill && target);
        els.back.disabled = tour.index <= tour.range.first;
        els.next.textContent = offRoute
            ? "Go to " + step.route
            : tour.index >= tour.range.last
            ? (tour.range.label ? "Finish part" : "Finish tour")
            : "Next";

        tour.callout.style.visibility = "hidden";
        measureCallout();
        tour.callout.style.visibility = "";

        if (target && target.scrollIntoView) {
            try {
                target.scrollIntoView({ block: "center", inline: "nearest" });
            } catch (e) {
                target.scrollIntoView();
            }
        }

        reposition();
        announce();

        // Keep the hole and the callout glued to the element while the page
        // scrolls, the panel slides, or the window is resized. This runs until the
        // tour stops (teardown cancels it).
        window.cancelAnimationFrame(tour.rafId);
        tour.rafId = window.requestAnimationFrame(followTarget);

        // Focus what the user has to use: the field for typing steps, otherwise
        // the callout (so screen readers read the instruction).
        var isField = target && /^(INPUT|SELECT|TEXTAREA)$/.test(target.tagName);
        if (isField && (step.action === "type" || step.action === "select")) {
            target.focus();
        } else {
            tour.callout.focus();
        }
    }

    function showStep(index, offRoute) {
        if (!tour.active) return;
        var step = STEPS[index];
        if (!step) {
            finishTour();
            return;
        }

        tour.index = index;
        tour.step = step;
        write("sessionStorage", KEYS.step, String(index));
        // Drop any debounce left over from the previous step, otherwise it fires
        // after the step changed and skips the new one.
        window.clearTimeout(tour.timer);

        ensureRoot();
        tour.root.style.display = "";
        window.clearTimeout(tour.menuTimer);

        // Steps about the panel — or about anything inside it — need it open; every
        // other step gets a clear screen. The selector is part of the test so a step
        // cannot end up highlighting the panel while the panel is being closed.
        var inPanel = !!(step.selector && step.selector.indexOf("#navSidebar") !== -1);
        var wantsMenu = !!step.inMenu || inPanel;
        var changed = setMenu(wantsMenu);

        // Give the panel's slide transition a moment before measuring it.
        tour.menuTimer = window.setTimeout(
            function () {
                renderStep(step, offRoute);
            },
            changed ? 400 : 0
        );
    }

    function advance() {
        if (!tour.active) return;
        window.clearTimeout(tour.timer);

        if (tour.offRoute) {
            // The stored step belongs to another page: go there and resume.
            window.location.assign(STEPS[tour.index].route.replace("*", ""));
            return;
        }

        var next = tour.index + 1;
        if (next > tour.range.last) {
            finishTour();
            return;
        }
        write("sessionStorage", KEYS.step, String(next));

        var step = STEPS[next];
        if (routeMatches(step.route, pathname())) {
            // Render after the current event finishes: the step that just completed
            // is usually a link, and the tour must not touch the DOM (or the
            // navigation panel) while that click is still being processed.
            window.setTimeout(function () {
                if (tour.active && tour.index === next - 1) showStep(next);
            }, 0);
            return;
        }

        // The step lives on another page. Usually the action that completed this
        // step triggers that navigation, so wait briefly before saying anything.
        var here = pathname();
        window.setTimeout(function () {
            if (!tour.active) return;
            if (pathname() !== here) return; // the page is navigating — nothing to do
            showStep(next, true);
        }, 700);
    }

    function goBack() {
        if (!tour.active || tour.index <= tour.range.first) return;
        var previous = tour.index - 1;
        var step = STEPS[previous];
        if (routeMatches(step.route, pathname())) {
            showStep(previous);
        } else {
            write("sessionStorage", KEYS.step, String(previous));
            window.location.assign(step.route.replace("*", ""));
        }
    }

    function fillExample() {
        var step = tour.step;
        if (!step || !step.fill || !tour.target) return;

        var field = tour.target;
        if (!/^(INPUT|SELECT|TEXTAREA)$/.test(field.tagName)) {
            field = field.querySelector("input, select, textarea");
        }
        if (!field) return;

        field.focus();
        field.value = step.fill;

        // Those events may complete the step on their own (the change handler
        // advances), so only schedule the follow-up while we are still here.
        var index = tour.index;
        field.dispatchEvent(new Event("input", { bubbles: true }));
        field.dispatchEvent(new Event("change", { bubbles: true }));
        if (tour.index !== index) return;

        tour.timer = window.setTimeout(function () {
            if (tour.index === index) advance();
        }, 420);
    }

    function teardown() {
        tour.active = false;
        tour.target = null;
        window.clearTimeout(tour.timer);
        window.clearTimeout(tour.menuTimer);
        window.cancelAnimationFrame(tour.rafId);
        if (tour.root) tour.root.style.display = "none";
    }

    function finishTour() {
        var label = tour.range.label;
        teardown();
        remove("sessionStorage", KEYS.active);
        remove("sessionStorage", KEYS.step);
        remove("sessionStorage", KEYS.section);
        write("localStorage", KEYS.seen, "1");
        toast(
            label
                ? "“" + label + "” finished — pick another part on the Tutorial page."
                : "Tour finished — replay it any time from the menu ▸ Tutorial."
        );
    }

    function exitTour(notify) {
        teardown();
        remove("sessionStorage", KEYS.active);
        remove("sessionStorage", KEYS.step);
        remove("sessionStorage", KEYS.section);
        if (notify) toast("Tutorial closed — replay it any time from the menu ▸ Tutorial.");
    }

    /**
     * Start the whole tour, or one section of it.
     * ``index`` picks a step inside the range (used by tests/console); ``sectionId``
     * picks the part from the Tutorial page.
     */
    function startTour(index, sectionId) {
        var range = rangeFor(sectionId);
        var start =
            typeof index === "number" && index >= range.first && index <= range.last
                ? index
                : range.first;

        tour.range = range;
        write("localStorage", KEYS.seen, "1");
        write("sessionStorage", KEYS.active, "1");
        write("sessionStorage", KEYS.step, String(start));
        write("sessionStorage", KEYS.section, range.section);

        tour.active = true;
        var step = STEPS[start];
        if (step && !routeMatches(step.route, pathname())) {
            window.location.assign(step.route.replace("*", ""));
            return;
        }
        showStep(start);
    }

    // ---------------------------------------------------------------------- //
    // Action detection — steps advance when the user really does the thing
    // ---------------------------------------------------------------------- //
    function matchesTarget(node) {
        if (!tour.target) return false;
        var el = node && node.nodeType === 1 ? node : null;
        if (!el) return false;
        if (el === tour.target || tour.target.contains(el)) return true;
        var closest = el.closest ? el.closest(tour.step.selector) : null;
        return !!closest && closest === tour.target;
    }

    document.addEventListener(
        "click",
        function (event) {
            if (!tour.active || !tour.step || tour.offRoute) return;
            if (tour.root && tour.root.contains(event.target)) return; // tour controls
            var action = tour.step.action;
            if (action !== "click" && action !== "submit") return;
            if (!matchesTarget(event.target)) return;
            advance();
        },
        true
    );

    document.addEventListener("input", function (event) {
        if (!tour.active || !tour.step || tour.step.action !== "type") return;
        if (!matchesTarget(event.target)) return;
        if (!String(event.target.value || "").trim()) return;
        window.clearTimeout(tour.timer);
        tour.timer = window.setTimeout(advance, 700);
    });

    document.addEventListener("change", function (event) {
        if (!tour.active || !tour.step || tour.offRoute) return;
        if (!matchesTarget(event.target)) return;
        if (tour.step.action === "select") {
            window.clearTimeout(tour.timer);
            advance();
        } else if (tour.step.action === "type") {
            // Leaving a field counts, but only with a value in it.
            if (!String(event.target.value || "").trim()) return;
            window.clearTimeout(tour.timer);
            advance();
        }
    });

    document.addEventListener(
        "submit",
        function (event) {
            if (!tour.active || !tour.step || tour.offRoute) return;
            if (tour.step.action !== "submit") return;
            if (!tour.target || !event.target.contains(tour.target)) return;
            advance();
        },
        true
    );

    document.addEventListener("keydown", function (event) {
        if (event.key !== "Escape") return;
        if (tour.active) {
            exitTour(true);
            return;
        }
        var welcome = document.querySelector(".tour-welcome-backdrop");
        if (welcome) skipWelcome(welcome);
    });

    window.addEventListener("resize", function () {
        if (!tour.active) return;
        measureCallout();
        tour.signature = "";
        reposition();
    });

    // ---------------------------------------------------------------------- //
    // First-run welcome
    // ---------------------------------------------------------------------- //
    function closeWelcome(backdrop) {
        if (backdrop && backdrop.parentNode) backdrop.remove();
    }

    function skipWelcome(backdrop) {
        write("localStorage", KEYS.seen, "1");
        closeWelcome(backdrop);
    }

    function showWelcome() {
        var backdrop = document.createElement("div");
        backdrop.className = "tour-welcome-backdrop";
        backdrop.innerHTML = [
            '<div class="tour-welcome" role="dialog" aria-modal="true"',
            '     aria-labelledby="tourWelcomeTitle">',
            '  <h2 id="tourWelcomeTitle">Welcome to the Student Performance Assistant</h2>',
            "  <p>This dashboard helps a lecturer see how a class is doing, early enough to act. ",
            "     It can:</p>",
            "  <ul>",
            "    <li><strong>Identify at-risk students</strong> — it works out the best and worst ",
            "        participation mark each student can still reach and flags anyone who cannot ",
            "        clear the pass threshold.</li>",
            "    <li><strong>Monitor performance</strong> — the dashboard and cohort table show the ",
            "        class average, the class size and who needs attention.</li>",
            "    <li><strong>Plan for the cohort</strong> — it proposes the marks a student needs on ",
            "        the assessments still to be written, and searches for assessment weights that ",
            "        move the class towards a target you choose.</li>",
            "  </ul>",
            "  <p>Let us create your first module together — the tour takes about three minutes ",
            "     and you can leave at any point.</p>",
            '  <div class="tour-welcome-actions">',
            '    <button type="button" class="btn tour-primary tour-glow" data-tour-go>',
            "      Let's start, create a module</button>",
            '    <button type="button" class="tour-skip-link" data-tour-skip>Skip</button>',
            "  </div>",
            '  <p class="tour-data-note">Simulated data only — everything lives in memory and ',
            "     resets when the app restarts. Never enter real student data.</p>",
            "</div>"
        ].join("\n");

        document.body.appendChild(backdrop);

        var primary = backdrop.querySelector("[data-tour-go]");
        var skip = backdrop.querySelector("[data-tour-skip]");
        if (primary) primary.focus();

        if (primary) {
            primary.addEventListener("click", function () {
                closeWelcome(backdrop);
                startTour(0);
            });
        }
        if (skip) {
            skip.addEventListener("click", function () {
                skipWelcome(backdrop);
            });
        }
        backdrop.addEventListener("keydown", function (event) {
            if (event.key !== "Tab") return;
            var items = backdrop.querySelectorAll("button, [href], input, select, textarea");
            if (!items.length) return;
            var first = items[0];
            var last = items[items.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        });
    }

    // ---------------------------------------------------------------------- //
    // Tutorial page controls + boot
    // ---------------------------------------------------------------------- //
    /** Render one card per section into the Tutorial page, from the same data. */
    function renderSectionChooser() {
        var host = document.querySelector("[data-tour-sections]");
        if (!host) return;

        host.innerHTML = SECTIONS.map(function (section) {
            var range = sectionRange(section.id);
            var count = range ? range.last - range.first + 1 : 0;
            return (
                '<article class="tour-section-card" data-section="' + section.id + '">' +
                "<h3>" + section.title + "</h3>" +
                '<p class="muted">' + section.blurb + "</p>" +
                '<p class="tour-section-meta">' + count + " steps</p>" +
                '<button type="button" class="btn btn-secondary" data-tour-section="' +
                section.id +
                '">Start this part</button>' +
                "</article>"
            );
        }).join("");

        host.addEventListener("click", function (event) {
            var button = event.target.closest ? event.target.closest("[data-tour-section]") : null;
            if (!button) return;
            startTour(null, button.getAttribute("data-tour-section"));
        });
    }

    function wireTutorialPage() {
        renderSectionChooser();

        var start = document.querySelector("[data-tour-start]");
        if (start) {
            start.addEventListener("click", function () {
                var route = start.getAttribute("data-tour-start-route") || "/";
                var range = rangeFor("");
                tour.range = range;
                write("localStorage", KEYS.seen, "1");
                write("sessionStorage", KEYS.active, "1");
                write("sessionStorage", KEYS.step, "0");
                write("sessionStorage", KEYS.section, "");
                if (!routeMatches(route, pathname())) {
                    window.location.assign(route);
                    return;
                }
                tour.active = true;
                showStep(0);
            });
        }

        var reset = document.querySelector("[data-tour-reset-welcome]");
        if (reset) {
            reset.addEventListener("change", function () {
                var status = document.getElementById("tourStatus");
                if (reset.checked) {
                    remove("localStorage", KEYS.seen);
                    if (status) {
                        status.textContent =
                            "The welcome message will appear again on your next visit.";
                    }
                } else {
                    write("localStorage", KEYS.seen, "1");
                    if (status) status.textContent = "Welcome message stays hidden.";
                }
            });
        }
    }

    function boot() {
        wireTutorialPage();

        var active = read("sessionStorage", KEYS.active) === "1";
        if (active) {
            var range = rangeFor(read("sessionStorage", KEYS.section) || "");
            tour.range = range;
            var index = parseInt(read("sessionStorage", KEYS.step) || "0", 10);
            if (isNaN(index) || index < 0 || index >= STEPS.length) {
                remove("sessionStorage", KEYS.active);
                remove("sessionStorage", KEYS.step);
                remove("sessionStorage", KEYS.section);
                return;
            }
            if (index < range.first || index > range.last) index = range.first;
            tour.active = true;
            if (routeMatches(STEPS[index].route, pathname())) {
                showStep(index);
            } else {
                showStep(index, true);
            }
            return;
        }

        // The tutorial page is itself the way in, so do not stack the first-run
        // popup on top of it.
        if (read("localStorage", KEYS.seen) !== "1" && pathname() !== "/tutorial") showWelcome();
    }

    // Expose a read-only handle for tests and for anyone exploring the steps.
    window.__dssTour = {
        steps: STEPS,
        sections: SECTIONS,
        start: startTour,
        state: function () {
            return { active: tour.active, index: tour.index };
        }
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", boot);
    } else {
        boot();
    }
})();
