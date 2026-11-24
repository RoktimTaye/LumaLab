## Context
React studio with three desktop columns and mobile panel tabs. The center holds the photo, the left holds upload and presets, and the right holds adjustment controls.

## Decisions
Keep this familiar editing layout. Use charcoal panels with a deeper canvas, flat borders, and green only for actions and selection. Keep the existing typefaces; use the body face for labels at 12–14px and monospace only for numeric values. Remove decorative panel numbers, status dots, repeated badges and marketing slogans. Use direct upload instructions. Thumbnails use the original image so an existing edit is not compounded in the preset thumbnail.

## Responsive behavior
Retain desktop column breakpoints and mobile panel tabs. Maintain 44px mobile controls. Keep presets in their existing bounded scroll area. Keep the image size governed by its aspect ratio.

## Risks
Scoped styles must not recolor image pixels or change slider event handlers. Home and header must remain unchanged.

## Validation
Production build and inspection of the scoped diff. Visual approval in the browser remains necessary; a build cannot certify appearance.
