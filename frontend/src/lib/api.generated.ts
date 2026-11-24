// Generated from backend OpenAPI; run npm run contracts:generate. Do not edit.
// Schema SHA-256: 50b3a1622e34928c9c13d81fd2011de71334b3230cdbe59c9d636672453a15ad
export interface components {
  schemas: {
    "Adjustments": { "brightness": number; "contrast": number; "saturation": number; "warmth": number; "sharpness": number; "vignette": number };
    "Body_upload_api_v1_images_post": { "file": Blob };
    "Crop": { "x": number; "y": number; "width": number; "height": number };
    "CurvePoint": { "x": number; "y": number };
    "Enhancement": { "adjustments": components["schemas"]["Adjustments"]; "message": string; "recipe"?: components["schemas"]["NaturalEnhancement"] | null; "assessment"?: Array<components["schemas"]["EnhancementFinding"]> };
    "EnhancementFinding": { "area": "light" | "contrast" | "color" | "detail"; "issue": string; "action": string; "observation"?: string };
    "ErrorDetail": { "code": string; "message": string };
    "ErrorResponse": { "error": components["schemas"]["ErrorDetail"] };
    "ExportRequest": { "adjustments": components["schemas"]["Adjustments"]; "curves"?: components["schemas"]["RGBCurves"] | null; "crop"?: components["schemas"]["Crop"] | null; "enhancement"?: components["schemas"]["NaturalEnhancement"] | null; "format"?: "jpeg"; "quality"?: 92 };
    "HealthResponse": { "status"?: "ready" };
    "NaturalEnhancement": { "version"?: "natural-v1" | "natural-v2" | "natural-v3"; "strength"?: number; "exposure_ev"?: number; "shadows"?: number; "highlights"?: number; "contrast"?: number; "vibrance"?: number; "red_gain"?: number; "green_gain"?: number; "blue_gain"?: number; "black_point"?: number; "white_lift"?: number; "tone_contrast"?: number; "clarity"?: number; "texture"?: number; "microcontrast"?: number; "detail_noise"?: number; "detail_reference_edge"?: number; "hue_chroma"?: Array<number>; "local_exposure"?: Array<number>; "base_luminance"?: Array<number> };
    "PointCurve": { "points": Array<components["schemas"]["CurvePoint"]> };
    "Preset": { "preset_id": string; "preset_name": string; "description": string; "brightness": number; "contrast": number; "saturation": number; "warmth": number; "sharpness": number; "vignette": number; "category": string; "popular": boolean; "display_order": number };
    "PreviewRequest": { "revision": number; "adjustments": components["schemas"]["Adjustments"]; "curves"?: components["schemas"]["RGBCurves"] | null; "crop"?: components["schemas"]["Crop"] | null; "enhancement"?: components["schemas"]["NaturalEnhancement"] | null };
    "RGBCurves": { "rgb"?: components["schemas"]["PointCurve"]; "red"?: components["schemas"]["PointCurve"]; "green"?: components["schemas"]["PointCurve"]; "blue"?: components["schemas"]["PointCurve"] };
    "UnavailableError": { "code"?: "service_unavailable"; "message"?: string };
    "UnavailableResponse": { "error": components["schemas"]["UnavailableError"] };
    "UploadedImage": { "image_id": string; "access_token": string; "filename": string; "format": "JPEG" | "PNG" | "WEBP"; "width": number; "height": number; "expires_at": string };
  };
}
export interface paths {
  "/api/v1/health": {
    get: {
      responses: {
        "200": { headers: {  }; content: { "application/json": components["schemas"]["HealthResponse"] } };
        "500": { headers: {  }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: {  }; content: { "application/json": components["schemas"]["UnavailableResponse"] } };
      };
    };
  };
  "/api/v1/images": {
    post: {
      requestBody: { content: { "multipart/form-data": components["schemas"]["Body_upload_api_v1_images_post"] } };
      responses: {
        "201": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["UploadedImage"] } };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "413": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "415": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/images/{image_id}": {
    delete: {
      parameters: { path: { "image_id": string } };
      responses: {
        "204": { headers: { "Cache-Control"?: "no-store" }; content?: never };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "401": { headers: { "Cache-Control"?: "no-store"; "WWW-Authenticate"?: "Bearer" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "404": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "410": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/images/{image_id}/enhance": {
    post: {
      parameters: { path: { "image_id": string } };
      responses: {
        "200": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["Enhancement"] } };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "401": { headers: { "Cache-Control"?: "no-store"; "WWW-Authenticate"?: "Bearer" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "404": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "410": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/images/{image_id}/export": {
    post: {
      parameters: { path: { "image_id": string } };
      requestBody: { content: { "application/json": components["schemas"]["ExportRequest"] } };
      responses: {
        "200": { headers: { "Cache-Control"?: "no-store"; "Content-Disposition"?: string }; content: { "image/jpeg": Blob } };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "401": { headers: { "Cache-Control"?: "no-store"; "WWW-Authenticate"?: "Bearer" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "404": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "410": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/images/{image_id}/original-preview": {
    get: {
      parameters: { path: { "image_id": string } };
      responses: {
        "200": { headers: { "Cache-Control"?: "no-store" }; content: { "image/jpeg": Blob } };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "401": { headers: { "Cache-Control"?: "no-store"; "WWW-Authenticate"?: "Bearer" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "404": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "410": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/images/{image_id}/preview": {
    post: {
      parameters: { path: { "image_id": string } };
      requestBody: { content: { "application/json": components["schemas"]["PreviewRequest"] } };
      responses: {
        "200": { headers: { "Cache-Control"?: "no-store"; "X-Image-Revision"?: number }; content: { "image/jpeg": Blob } };
        "400": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "401": { headers: { "Cache-Control"?: "no-store"; "WWW-Authenticate"?: "Bearer" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "404": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "410": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "429": { headers: { "Cache-Control"?: "no-store"; "Retry-After"?: number }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: { "Cache-Control"?: "no-store" }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
      };
    };
  };
  "/api/v1/presets": {
    get: {
      responses: {
        "200": { headers: {  }; content: { "application/json": Array<components["schemas"]["Preset"]> } };
        "500": { headers: {  }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: {  }; content: { "application/json": components["schemas"]["UnavailableResponse"] } };
      };
    };
  };
  "/api/v1/presets/{preset_id}": {
    get: {
      parameters: { path: { "preset_id": string } };
      responses: {
        "200": { headers: {  }; content: { "application/json": components["schemas"]["Preset"] } };
        "404": { headers: {  }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "422": { headers: {  }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "500": { headers: {  }; content: { "application/json": components["schemas"]["ErrorResponse"] } };
        "503": { headers: {  }; content: { "application/json": components["schemas"]["UnavailableResponse"] } };
      };
    };
  };
}
