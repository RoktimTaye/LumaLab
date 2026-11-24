## ADDED Requirements
### Requirement: A restrained editing workbench
The studio SHALL give the photograph visual priority using neutral panels, readable labels, and direct task copy.

#### Scenario: Empty studio
- **WHEN** the studio opens without a photograph
- **THEN** it shows a concise upload heading, supported formats, and the existing sample action
- **AND** decorative slogans and panel numbering do not compete with these actions

### Requirement: Existing editing behavior is preserved
The studio SHALL retain upload, preset loading, live adjustments, curves, crop, comparison, detail, export and reset behavior.

#### Scenario: Preset selection
- **WHEN** a user selects a preset
- **THEN** its existing immediate preview and lazy backend loading continue to work
- **AND** category expansion and independent preset scrolling remain available

### Requirement: Responsive scope
The redesign SHALL affect only the studio and retain its mobile panel controls.

#### Scenario: Mobile studio
- **WHEN** the viewport is narrower than 768px
- **THEN** presets and adjustments remain accessible through their existing tabs
- **AND** touch controls have a minimum 44px target
