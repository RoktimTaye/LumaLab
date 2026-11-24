ALTER TABLE public.presets
    ADD COLUMN category TEXT NOT NULL DEFAULT 'Essentials'
        CHECK (category IN ('Popular', 'Portrait', 'Landscape', 'Film & Vintage', 'Black & White', 'Creative', 'Essentials')),
    ADD COLUMN popular BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0 CHECK (display_order BETWEEN 0 AND 1000);
