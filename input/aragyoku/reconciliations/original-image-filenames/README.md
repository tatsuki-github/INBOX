# Original image filename preservation

These byte-identical copies preserve image paths introduced before the final
content-based filename reconciliation. Canonical searchable copies remain in
`input/aragyoku/images/`:

- `2023_female_..._02.jpg` -> `images/2023_female_..._01.jpg`
- `2025_male_..._02.jpg` -> `images/2025_female_..._01.jpg`
- `2025_male_..._03.jpg` -> `images/2025_male_..._01.jpg`

The copies are retained so the reconciliation does not remove existing image
data, including the two paths whose original gender/year assignment was wrong.
