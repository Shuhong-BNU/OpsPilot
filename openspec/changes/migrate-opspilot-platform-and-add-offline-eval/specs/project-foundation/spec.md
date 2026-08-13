## MODIFIED Requirements

### Requirement: Repository foundation
OpsPilot SHALL provide a local-first repository foundation with a Python backend, Vue frontend, shared contracts, local configuration templates, infrastructure assets, and versioned documentation.

#### Scenario: Backend package identity

- **WHEN** backend code or a backend command imports the application package
- **THEN** it MUST use `opspilot` rather than a legacy package name, and the health payload MUST identify service `opspilot-backend` at version `1.2.1`.

#### Scenario: Product identity

- **WHEN** a developer reads the repository README, configuration templates, Compose asset, package metadata, or generated API contract
- **THEN** the current product identity MUST be OpsPilot and MUST NOT present an old project name as the current product.
