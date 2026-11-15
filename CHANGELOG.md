# Changelog

## Unreleased — 0.2.4-dev

- Release comparison anchors when the shared tooltip changes item or owner.
- Keep quest items and other non-equippable loot on the native tooltip path.
- Clear stale comparison state when loot opens/closes or the source tooltip hides.
- Add tests for gear-to-quest transitions and native loot content preservation.

## 0.2.3 ? 2026-11-15

Tooltip stability and layout fixes, verified in game.

- Fix disappearing comparison tooltips: retain item data while arranging visible cards.
- Prevent the hovered tooltip from jumping during native tooltip updates.
- Use actual tooltip widths for consistent spacing and expand headers for wrapped set names.
- Restore item badges on anonymous buttons in the combined backpack.
- Support modern tooltip payloads, GUID links, and embedded item tooltips.
- Improve comparison error reporting and add `/gst comparedebug`.
- Extend tests for complete addon startup, tooltip clearing on hide, pagination, and anchor stability.

Versions 0.2.3?0.2.7 used during local debugging were not public releases;
these fixes are consolidated into this single public 0.2.3 release.

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
