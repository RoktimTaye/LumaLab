# Crop and aspect ratio

Open a photograph in the Studio and choose **Crop** below the preview. Choose
Freeform, Original, or a landscape, square, portrait, or social aspect ratio.
Drag the frame to reposition it and drag a corner to resize it. The pixel fields
provide the same controls without a pointer; focus the frame and use arrow keys
to move it by one pixel, or Shift + arrow keys to move by ten pixels.

**Apply crop** updates the backend preview. **Cancel** and Escape discard the
draft. **Reset crop**, followed by Apply, restores the full photograph. Presets,
Auto Enhance, and Reset adjustments preserve the crop. Comparison shows the
same crop of the original against the edited image. JPEG export uses the chosen
crop's full pixel dimensions, which are shown in the export dialog.

Cropping is non-destructive. Replacement photographs start with no crop. No crop
drafts or image tokens are written to persistent browser storage.

Preview and export requests accept an optional `crop` object with strict integer
`x`, `y`, `width`, and `height` fields measured in oriented original-image pixels.
Omitting it or sending `null` preserves the previous full-frame API behavior.
The backend rejects empty, oversized, or out-of-bounds rectangles with 422 and
keeps existing authorization, capacity limits, and no-store responses. Preview
work stays on the existing reduced-resolution source; only export reads the
full normalized image. Dragging a crop sends no processing requests until Apply.
