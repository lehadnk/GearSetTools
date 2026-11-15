# Changelog

## 0.2.2 — 2026-11-15

First public beta for WoW Forever (interface 16001).

- Mark items from Blizzard equipment sets with the saved set's icon in standard bags and bank.
- Compare a hovered item with current equipment and every saved equipment set using full tooltips.
- Keep the hovered item first, omit empty or ignored slots, and merge equipped/set duplicates.
- Show stat changes, both ring/trinket alternatives, and combined two-handed weapon replacements.
- Page overflowing comparisons with Alt while comparison remains active.
- Save full bank item links per character across reloads and logouts.
- Resolve banked set members when Forever reports their location as -1; ambiguous variants stay unresolved.
- Provide `/gst debug`, `/gst cache`, `/gst next`, and `/gst hover` diagnostics.

Known limitations: standard Blizzard bags/bank only; one set icon per marked item;
single-slot weapon comparisons do not assume an off-hand partner. Bank data is a
last-seen snapshot until the next visit. If several variants share an unresolved
set item ID, the addon cannot reliably choose one.
