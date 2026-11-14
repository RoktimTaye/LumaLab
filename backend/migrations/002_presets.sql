CREATE TABLE public.presets (
    preset_id TEXT PRIMARY KEY,
    preset_name TEXT NOT NULL,
    description TEXT NOT NULL,
    brightness INTEGER NOT NULL CHECK (brightness BETWEEN 0 AND 200),
    contrast INTEGER NOT NULL CHECK (contrast BETWEEN 0 AND 200),
    saturation INTEGER NOT NULL CHECK (saturation BETWEEN 0 AND 200),
    warmth INTEGER NOT NULL CHECK (warmth BETWEEN -50 AND 50),
    sharpness INTEGER NOT NULL CHECK (sharpness BETWEEN 0 AND 100),
    vignette INTEGER NOT NULL CHECK (vignette BETWEEN 0 AND 100)
);

GRANT SELECT ON public.presets TO lumalab_app;
