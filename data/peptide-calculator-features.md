# Peptide Calculator — Feature Overview

## What It Is

A web-based peptide reconstitution calculator that tells users exactly how much bacteriostatic water to add to their vial and how many units to draw on their syringe for a given dose. It supports individual peptides, multi-component compound blends, three syringe sizes, automatic and manual mixing modes, shareable URLs, and a vial + dose tracking system.

---

## Supported Peptides

The calculator ships with a built-in database of 15 individual peptides and 4
compound blends, organized into six categories:

### Weight Loss / Metabolic
- **Semaglutide** (`semaglutide`) — GLP-1 agonist (vials: 3, 5, 10, 20 mg)
- **Tirzepatide** (`tirzepatide`) — Dual GLP-1/GIP agonist (vials: 5, 10, 15, 30, 60 mg)
- **Retatrutide** (`retatrutide`) — Triple agonist (vials: 10, 15, 20, 30 mg)
- **Cagrilintide** (`cagrilintide`) — Amylin analog (vials: 5, 10, 20 mg)

### Repair / Regeneration
- **BPC-157** (`bpc-157`) — Tissue healing and gut repair (vials: 5, 10 mg)
- **TB-500** (`tb-500`) — Injury recovery and flexibility (vials: 5, 10 mg)
- **GHK-Cu** (`ghk-cu`) — Skin rejuvenation and wound healing (vials: 10, 50 mg)
- **KPV** (`kpv`) — Anti-inflammatory tripeptide (vials: 5, 10 mg)

### Cosmetic
- **Melanotan I** (`melanotan-1`) — Gradual tanning (vials: 10 mg)
- **Melanotan II** (`melanotan-2`) — Rapid tanning and libido (vials: 10 mg)

### Growth Hormone
- **HGH** (`hgh`) — Human Growth Hormone with IU support (vials: 4, 10, 12 mg)
- **CJC-1295** (`cjc-1295`) — GH secretagogue (vials: 2, 5 mg)
- **Ipamorelin** (`ipamorelin`) — GH secretagogue (vials: 2, 5 mg)

### Blends
- **Glow** (`glow`) — GHK-Cu + BPC-157 + TB-500 compound blend
- **Wolverine** (`wolverine`) — BPC-157 + TB-500 compound blend
- **KLOW** (`klow`) — GHK-Cu + KPV + BPC-157 + TB-500 compound blend
- **CJC / Ipamorelin** (`cjc-1295-ipamorelin`) — CJC-1295 + Ipamorelin compound blend

### Custom / Other
- **PT-141** (`pt-141`) — Sexual health (vials: 10 mg)
- **Custom peptide** (`custom`) — Fully user-defined peptide with custom parameters

---

## Core Calculator Features

### Smart Auto-Mix Recommendation

When the user selects a peptide, vial size, dose, and syringe, the calculator automatically recommends the best water amount and draw volume. The recommendation algorithm:

- Iterates through every possible draw volume that lands on an actual tick mark on the selected syringe
- Filters for safety constraints (max injection volume, concentration limits, minimum water)
- Scores remaining options by convenience factors:
  - Lands on a major tick mark (easier to draw accurately)
  - Uses a round water amount (e.g., 1 ml, 2 ml)
  - Creates easy mental math (e.g., 10 units = 1 mg)
  - Smaller draw volumes preferred
- Presents the single best recommendation with a plain-English result: "Add **X ml** water, Draw to **Y** units"

### Manual Mode

Users can toggle from Auto to Manual mode at any time. Manual mode lets the user enter any custom water amount and instantly see the resulting draw volume in units. Includes real-time validation:

- Warns when draw volume exceeds syringe capacity
- Validates water amount bounds (positive, max 10 ml)

### "How We Calculate" Explainer

A full-screen animated modal (with gradient overlay and breathing animation) explains the calculation rules, safety constraints, preference scoring, and disclaimers in plain language.

---

## Compound Blend Support

Four pre-configured compound blends (Glow, Wolverine, KLOW, CJC/Ipamorelin) demonstrate the calculator's multi-component blend capabilities:

- **Pre-set ratios**: Each blend has default component amounts (e.g., Glow = 50 mg GHK-Cu / 10 mg BPC-157 / 10 mg TB-500, CJC/Ipamorelin = 3 mg each)
- **Custom component amounts**: Users can tap "Other" to enter individual mg amounts for each component in the blend, overriding the default ratios
- **Anchor-based dosing**: Doses are specified in terms of the primary (anchor) component, and the calculator automatically shows the proportional dose breakdown for every component in the blend
- **Dose breakdown display**: A detailed breakdown appears showing exactly how much of each component the user will receive per injection
- **Per-component concentration limits**: The calculator enforces each individual component's maximum concentration, ensuring no single ingredient exceeds safe thresholds even when mixed together

---

## Unit System

### Flexible Unit Input

Both vial size and dose support three units with automatic conversion:

- **mg** (milligrams)
- **mcg** (micrograms)
- **IU** (International Units) — available when the peptide defines an IU-to-mg ratio (e.g., HGH at 3 IU per mg)

When the user switches units, the entered value is automatically converted to the equivalent amount in the new unit (e.g., switching from 500 mcg to mg shows 0.5).

### Preset Dose Units

Each peptide defines its doses in the most natural unit for that peptide:
- Weight loss peptides use mg (e.g., Semaglutide 0.25 mg, 0.5 mg, 1 mg)
- Healing peptides use mcg (e.g., BPC-157 250 mcg, 500 mcg)
- HGH uses IU (e.g., 1 IU, 2 IU, 3 IU)

---

## Syringe Support

Three insulin syringe sizes with accurate tick mark rendering:

| Syringe | Total Units | Major Marks Every | Step Size |
|---------|------------|-------------------|-----------|
| 0.3 ml  | 30 units   | 5 units           | 1 unit    |
| 0.5 ml  | 50 units   | 5 units           | 1 unit    |
| 1.0 ml  | 100 units  | 10 units          | 2 units   |

### Visual Syringe Illustration

An interactive syringe graphic with:
- Accurate tick marks matching the selected syringe size
- Major and minor tick marks with unit labels
- Animated fill indicator showing the calculated draw volume
- Red fill color when the draw volume overflows the syringe capacity
- Reduced opacity on overflow to signal the issue visually

---

## Quick-Select UI

Both vial size and dose use a "quick-select card" pattern:

- **Preset buttons**: The most common options appear as tap-friendly buttons (up to 4 visible, additional options shown when "Other" is expanded)
- **"Other" mode**: Expands a text input with unit selector for entering any custom value
- **Overflow options**: If a peptide has more than 4 presets, the extras appear in a second row when "Other" is active
- **Compound vial labels**: For blends, preset buttons show the component breakdown (e.g., "70 mg (50/10/10)")

---

## Vial Management

### Save Vials

After calculating a mix, users can save the vial configuration with one tap. Saved data includes:
- Peptide type
- Total vial mg
- Water amount used
- Component amounts (for compound blends)
- Mix date

### My Vials Tab

A dedicated "My Vials" tab appears once at least one vial is saved. Each vial card shows:
- Peptide name
- Vial mg, water ml, and days since mixed
- Delete option

### Dose Logging

Each saved vial has a "Log Dose" button that lets users record:
- Units drawn
- Injection site (optional): Abdomen L/R, Thigh L/R, Arm L/R, Glute L/R
- Timestamp (automatic)

Recent dose history (last 3 entries) is displayed on each vial card with units, injection site, and date.

---

## Shareable URLs & Pre-Loaded Links

Every calculator state is encoded in the URL in real time. Users can copy and share a link that restores the exact calculator state for another person. More importantly, marketers and partners can craft URLs that pre-fill some fields while leaving others empty, guiding the user to complete only the remaining steps.

### URL Parameters

All parameters are optional. Only `peptide` is needed to activate the calculator; everything else fills in progressively.

| Parameter    | Required | Default when omitted | Description                                      |
|-------------|----------|----------------------|--------------------------------------------------|
| `peptide`   | No       | No peptide selected  | Peptide key (see table below)                    |
| `vial`      | No       | None (user must pick) | Vial amount as a number                         |
| `vial_unit` | No       | `mg`                 | Unit for vial amount: `mg`, `mcg`, or `IU`       |
| `dose`      | No       | None (user must pick) | Dose amount as a number                         |
| `dose_unit` | No       | Peptide's native unit| Unit for dose: `mg`, `mcg`, or `IU`              |
| `syringe`   | No       | None (user must pick) | Syringe capacity: `0.3`, `0.5`, or `1`          |
| `water`     | No       | Auto mode            | Water amount in ml. When present, the calculator opens in manual mode instead of auto mode (see below) |
| `compound_<key>` | No | Default blend ratios | Per-component mg amount, where `<key>` is the hyphenated peptide key (e.g., `compound_ghk-cu=50&compound_bpc-157=10`) |

### Peptide Keys

All keys use hyphenated format.

**Individual peptides:**

| Key                  | Peptide Name              |
|----------------------|---------------------------|
| `semaglutide`        | Semaglutide               |
| `tirzepatide`        | Tirzepatide               |
| `retatrutide`        | Retatrutide               |
| `cagrilintide`       | Cagrilintide              |
| `bpc-157`            | BPC-157                   |
| `tb-500`             | TB-500                    |
| `ghk-cu`             | GHK-Cu                    |
| `kpv`                | KPV                       |
| `melanotan-1`        | Melanotan I               |
| `melanotan-2`        | Melanotan II              |
| `hgh`                | HGH                       |
| `cjc-1295`           | CJC-1295                  |
| `ipamorelin`         | Ipamorelin                |
| `pt-141`             | PT-141                    |
| `custom`             | Custom peptide             |

**Compound blends:**

| Key                    | Blend Name                  | Components                    |
|------------------------|-----------------------------|-------------------------------|
| `glow`                 | Glow                        | GHK-Cu + BPC-157 + TB-500    |
| `wolverine`            | Wolverine                   | BPC-157 + TB-500              |
| `klow`                 | KLOW                        | GHK-Cu + KPV + BPC-157 + TB-500 |
| `cjc-1295-ipamorelin`  | CJC / Ipamorelin            | CJC-1295 + Ipamorelin         |

### Pre-Filling Strategy: Leave Fields Out to Force User Action

Every omitted parameter becomes a field the user must fill in before a result appears. This is by design — the calculator shows a disabled placeholder state ("Select a vial size and dose") until all required inputs are provided. You can use this to build guided funnels:

**Full result link** — User sees the answer immediately:
```
?peptide=semaglutide&vial=10&dose=0.5&dose_unit=mg&syringe=1
```

**Peptide + vial pre-filled, user picks dose and syringe:**
```
?peptide=semaglutide&vial=10
```
The calculator opens with Semaglutide selected and 10 mg highlighted. The dose card and syringe are in their default states, waiting for input. No result appears until both are chosen.

**Peptide only** — User picks everything else:
```
?peptide=tirzepatide
```
Opens with Tirzepatide selected. Vial, dose, and syringe cards are all in their initial state. The syringe defaults to unselected (no capacity chosen), so the user must interact with all three before seeing a recommendation.

**Peptide + dose, no vial** — Useful when a provider prescribes a dose but the user's vial size varies:
```
?peptide=semaglutide&dose=1&dose_unit=mg
```
Opens with Semaglutide at 1 mg dose pre-filled. User only needs to enter their vial size and pick a syringe.

**Compound blend with custom component amounts:**
```
?peptide=glow&compound_ghk-cu=50&compound_bpc-157=10&compound_tb-500=10
```
Opens the Glow blend with "Other" mode active and each component's mg pre-filled. Omitting the compound params (and `vial`) leaves the component inputs empty for the user to fill.

**Compound blend with dose and syringe — full result:**
```
?peptide=glow&compound_ghk-cu=50&compound_bpc-157=10&compound_tb-500=10&dose=500&dose_unit=mcg&syringe=0.5
```
Opens Glow with custom component amounts, a 500 mcg dose, and 0.5 ml syringe. The user sees a recommendation immediately.

**Wolverine blend, user picks dose and syringe:**
```
?peptide=wolverine&compound_bpc-157=5&compound_tb-500=5
```
Opens Wolverine with 5 mg of each component pre-filled. Dose and syringe are left for the user to select.

**KLOW blend with all four components:**
```
?peptide=klow&compound_ghk-cu=50&compound_kpv=10&compound_bpc-157=10&compound_tb-500=10&dose=250&dose_unit=mcg&syringe=1
```
Opens the full KLOW blend with all components specified and a complete calculation ready.

**Compound blend with preset vial (no custom components):**
```
?peptide=wolverine&vial=20&dose=500&dose_unit=mcg&syringe=0.5
```
Opens Wolverine using the 20 mg preset vial instead of custom component amounts. Since `vial` is present, the compound params are ignored and the default ratio is used.

**CJC-1295 + Ipamorelin blend:**
```
?peptide=cjc-1295-ipamorelin&compound_cjc-1295=3&compound_ipamorelin=3&dose=200&dose_unit=mcg&syringe=1
```
Opens the CJC / Ipamorelin blend with 3 mg of each component and a 200 mcg dose.

**HGH with IU units:**
```
?peptide=hgh&vial=12&dose=2&dose_unit=IU&syringe=1
```
Opens HGH with a 12 mg vial and 2 IU dose using the 1 ml syringe.

**Manual mode — auto mode has no recommendation (large vial, tiny dose):**
```
?peptide=custom&vial=50&dose=750&dose_unit=mcg&syringe=0.3&water=2.5
```
A 50 mg custom peptide vial with a 750 mcg dose on a 0.3 ml syringe. The concentration limits force at least 2.5 ml of water, but at that dilution the draw volume (1.125 units) doesn't land on any tick mark of the 0.3 ml syringe. Auto mode shows "No recommendation for these options" and links to manual mode, where the user can enter their own water amount and see the exact (non-round) draw volume.

**Manual mode — auto mode has no recommendation (small syringe, high concentration):**
```
?peptide=tirzepatide&vial=60&dose=5&dose_unit=mg&syringe=0.3&water=2
```
A 60 mg Tirzepatide vial with a 5 mg dose. The high vial size limits feasible water/draw combinations on the small 0.3 ml syringe. When auto mode can't find a draw that lands cleanly on a major tick mark within all safety constraints, the user switches to manual mode and enters their preferred water amount directly.

**⚠️ URL RULES:**
- **Trailing slash always**: `/peptides/?peptide=...` not `/peptides?peptide=...`
- **Always include syringe**: default to `&syringe=1` (1ml) unless the post specifies a different size (0.3 or 0.5)

**Manual mode — user already knows their water amount:**
```
?peptide=bpc-157&vial=5&dose=500&dose_unit=mcg&syringe=0.5&water=2
```
The presence of `water` switches the calculator from auto mode (where it recommends the best water amount) to manual mode (where the user specifies their own). Here the user has already added 2 ml to their vial and just wants to know how many units to draw.

**Manual mode — compound blend with known water:**
```
?peptide=glow&compound_ghk-cu=50&compound_bpc-157=10&compound_tb-500=10&dose=500&dose_unit=mcg&syringe=0.5&water=1.5
```
Same idea for a compound blend. The user mixed their Glow vial with 1.5 ml of water and wants the draw volume. Omitting `water` from either of these URLs would switch back to auto mode, where the calculator recommends the optimal water amount.

### Behavior Details

- When `peptide` is present but `syringe` is absent, the syringe defaults to **unselected** (user must pick). When `peptide` is absent entirely, the syringe defaults to 1 ml.
- `dose_unit` defaults to the peptide's most natural unit when omitted (e.g., `mg` for Semaglutide, `mcg` for BPC-157, `IU` for HGH).
- `vial_unit` defaults to `mg` when omitted.
- For compound blends, `vial` and `compound_<key>` params are mutually exclusive. If `vial` is present, it selects a preset total vial size. If compound params are present (and `vial` is absent), it activates "Other" mode with per-component inputs. The `<key>` in `compound_<key>` uses the same hyphenated peptide key (e.g., `compound_bpc-157`, `compound_ghk-cu`).
- The `water` parameter controls auto vs. manual mode. When absent, the calculator recommends the optimal water amount (auto mode). When present, the calculator uses the specified water amount and shows the resulting draw volume (manual mode). Manual mode is useful when a user has already reconstituted their vial and just needs to know how many units to draw.
- The URL updates in real time as the user interacts with the calculator, so any shared link always reflects the latest state.

---

## Custom Peptide Entry

The "Custom peptide" option allows users to calculate for any peptide not in the database. It provides:
- Common vial size presets (2, 5, 10, 50 mg) plus free-form entry
- Common dose presets (250 mcg, 500 mcg, 1 mg, 2 mg) plus free-form entry
- Full unit conversion and auto/manual mode support

---

## Safety Guardrails

The calculator enforces multiple safety constraints:

- **Maximum subcutaneous injection volume**: 0.5 ml per dose
- **Per-peptide concentration limits**: Some peptides (Tirzepatide, GHK-Cu) have custom max concentrations; all others default to 20 mg/ml
- **Absolute concentration ceiling**: 100 mg/ml hard cap
- **Minimum water**: At least 0.3 ml per vial
- **Maximum water**: 3 ml per vial (auto mode), 10 ml (manual mode)
- **Syringe overflow detection**: Visual warning when calculated draw exceeds syringe capacity

When no safe auto recommendation exists, the calculator clearly states "No recommendation for these options" and links the user to manual mode.

---

## Analytics & Tracking

The calculator tracks key user interactions for product insights:

- Peptide selection (name, category)
- Vial size selection (value, unit, quick-select vs. custom)
- Dose selection (value, unit, quick-select vs. custom)
- Syringe changes
- Completed calculations (recommended water and units)
- Mode switches (auto to manual, with context on whether auto had results)
- Vial saves
- Link shares
- URL-restored sessions
- "How we calculate" modal views

---

## Design & UX Details

- **Categorized peptide dropdown**: Peptides are grouped by category with descriptions, using a searchable listbox component
- **Animated "How We Calculate" modal**: Full-screen overlay with indigo gradient breathing animation, blur backdrop, and spring-based entrance/exit transitions
- **Responsive card layout**: All cards use consistent rounded corners, outlines, and spacing
- **Disabled states**: Cards show placeholder content with reduced opacity when prerequisites aren't met
- **Tab navigation**: Calculator and My Vials tabs with custom SVG icons; vials tab auto-hides when empty
