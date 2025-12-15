# Nebulatro: Mapping GUI Labeling Output -> Canonical State JSON

This note describes how to map the current Nebulatro GUI labeling structures into the canonical state JSON (validated by `schema/state_schema.json`).

## 1) Two JSONs exist on purpose

**A. Annotation JSON (per-image)**
- Stored alongside images in `dataset/annotations/<image_id>.json`
- Friendly for labeling (slots, partial counters, unknown fields)

**B. Canonical State JSON (policy input)**
- Deterministic keys for decision logic
- Validated by `schema/state_schema.json`
- Recommended storage: `dataset/states/<image_id>.state.json`

Canonical state should be derived from annotation JSON + any counters you can read.

## 2) Mapping rules

### screen
- `screen.type`: one of `play`, `shop`, `pack`, `blind_select`, `menu`, `unknown`
- `screen.substate`: stable string you define (examples: `select_cards`, `choose_pack`, `reroll`)

### hand
For each card in hand:
- `rank`: 2..10,J,Q,K,A
- `suit`: spades/hearts/clubs/diamonds
- `edition`: null | foil | holographic | polychrome
- `enhancements`: list of `bonus,mult,wild,lucky,glass,steel,stone,gold`
- `seal`: null | gold | purple | red | blue
- `id`: computed as `{rank}_{suit}` (example: `A_spades`)

### jokers
- If unknown: `[]`
- If known: `id` as your stable slug (example: `blue_joker`), with `slot` 0-9

### vouchers (owned/active)
- If you do not track vouchers yet, emit `[]`.
- If you do, emit stable slugs:
  - `vouchers: [{"id": "clearance_sale"}, {"id": "overstock"}]`

### shop (offers)
- If not on the shop screen, you can emit:
  - `shop: {"offers": []}`
- If in shop, list what is currently purchasable:
  - `offers: [{"type":"voucher","id":"clearance_sale","price":10}, ...]`

### economy / round / score
These keys are required by the schema. If you cannot read them yet, set 0 / unknown consistently.
- `economy.money`
- `economy.interest_cap`
- `round.ante`
- `round.blind` (small/big/boss/unknown)
- `round.hands_left`
- `round.discards_left`
- `score.current`
- `score.required`

### rng_visible
- Use `false` unless you explicitly detect an RNG UI element.

## 3) Minimal valid canonical state

```json
{
  "schema_version": "1.1",
  "screen": {"type": "play", "substate": "select_cards"},
  "hand": [],
  "played_cards": [],
  "jokers": [],
  "vouchers": [],
  "economy": {"money": 0, "interest_cap": 0},
  "round": {"ante": 0, "blind": "unknown", "hands_left": 0, "discards_left": 0},
  "score": {"current": 0, "required": 0},
  "rng_visible": false,
  "shop": {"offers": []}
}
```

## 4) Low-touch integration point

In the GUI labeling confirm action:
1. Save annotation JSON
2. Build canonical state JSON using the mapping rules
3. Validate with `validate_state(state)`
4. Save to `dataset/states/<image_id>.state.json`
