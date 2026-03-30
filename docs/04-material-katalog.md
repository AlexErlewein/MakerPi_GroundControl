# Material Catalog

The material catalog defines reusable, priced material entries that can be attached to Laufzettel records.

## Hierarchy

The catalog has three levels:

- **Location**
- **Category**
- **Variant**

Example:

```text
Töpferei
  └─ Ton
       ├─ fein
       └─ grob

Holz-Werkstatt
  └─ Holz
       ├─ Eiche
       ├─ Esche
       └─ Altholz
```

## Why the hierarchy exists

### Location

A location groups materials by workshop area.

Examples:

- `Töpferei`
- `Holz-Werkstatt`
- `FabLab`

### Category

A category defines how pricing works.

Examples:

- `Ton`
- `Holz`
- future FabLab categories

### Variant

A variant is the priced selectable option.

Examples:

- `fein`
- `grob`
- `Eiche`
- `Esche`

## Pricing models

### `per_gram`

Use for materials like Ton.

Fields entered on the Laufzettel:

- amount in grams

Formula:

```text
price = grams × unit_price
```

### `per_volume_cm3`

Use for materials like Holz.

Fields entered on the Laufzettel:

- length in cm
- width in cm
- height in cm

Formula:

```text
volume_cm3 = length × width × height
price = volume_cm3 × unit_price
```

### `per_unit`

Use for generic or future categories.

Fields entered on the Laufzettel:

- amount

Formula:

```text
price = amount × unit_price
```

## Stored values on Laufzettel material

Catalog-backed Laufzettel material entries can store:

- selected variant ID
- unit
- dimensions
- calculated price

This means the historical price result is preserved even if the catalog changes later.

## Practical examples

### Ton

- location: `Töpferei`
- category: `Ton`
- pricing model: `per_gram`
- variants: `fein`, `grob`

### Holz

- location: `Holz-Werkstatt`
- category: `Holz`
- pricing model: `per_volume_cm3`
- variants: `Eiche`, `Esche`, `Altholz`

### FabLab

Current recommendation:

- start with `per_unit`
- introduce more specific pricing models only when the workflow becomes clear
