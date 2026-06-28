# HL Docs Guide

This folder is a project documentation template pack. It is intended to give a new project a consistent structure for product definition, technical planning, execution tracking, deployment readiness, and supporting reference material.

## Purpose

Use `hl-docs` to answer five different questions:

1. What are we building?
2. How should it be designed technically?
3. In what order should it be implemented?
4. How will it be deployed and operated?
5. What external assets or supporting materials does the team need?

These questions should be answered by different documents. Do not collapse them into one file.

## Document Roles

### 1. Product Requirements Document
File: `[project-name]-prd.md`

This is the product source of truth.

Use it for:
- business objective
- problem statement
- user types
- feature scope
- platform scope
- shared product rules
- security or compliance requirements at product level

Do not use it for:
- repo folder structure
- endpoint implementation details
- task checklists
- deployment commands

### 2. Platform Build Plans
Files:
- `web-docs/web-build-plan.md`
- `backend-docs/backend-build-plan.md`
- `mobile-docs/mobile-build-plan.md`

These are the architecture and implementation-shape source of truth for each platform.

Use them for:
- framework choices
- directory conventions
- state management patterns
- API/data flow expectations
- auth and route protection patterns
- third-party integration strategy

Do not use them for:
- feature-by-feature progress tracking
- detailed phase tasks
- product scope decisions that affect all platforms

### 3. Execution Workflows
Files:
- `web-docs/execution-workflow.md`
- `backend-docs/execution-workflow.md`
- `mobile-docs/execution-workflow.md`

These are the delivery tracking documents for each platform.

Use them for:
- implementation order
- phase status
- phase dependencies
- readiness tracking
- execution log summaries

Do not use them for:
- architecture rationale
- full acceptance criteria for a feature
- detailed code insertion instructions

### 4. Phase Documents
Pattern:
- `phase-00-name.md`
- `phase-00a-name.md`

These are the implementation-control documents used during execution.

Use them for:
- exact task scope
- prerequisites
- affected files
- data contract details
- verification steps
- execution evidence

Each phase doc should point back to:
- the platform execution workflow
- the project PRD

### 5. Deployment Documents
Folder: `deployment-docs/`

Use these for:
- setup instructions
- infra prerequisites
- credentials and environment preparation guidance
- runbooks
- operations procedures

### 6. Reference Documents
Folder: `reference-docs/`

Use this folder for supporting artifacts such as:
- design exports
- wireframes
- seed data
- vendor specs
- third-party integration references

Reference docs support planning. They are not the source of truth for requirements or architecture.

## Recommended Order Of Use

For a new project, use the documents in this order:

1. Fill `[project-name]-prd.md`
2. Keep only the platform folders that are actually in scope
3. Fill the relevant platform build plan documents
4. Create the matching execution workflow documents
5. Create phase files from the phase template as implementation begins
6. Fill deployment docs before release-critical work starts
7. Attach design specs, payload samples, or vendor references in `reference-docs/`

## Source Of Truth Rules

Use these ownership rules to avoid overlap:

- Product scope lives in the PRD
- Platform architecture lives in that platform's build plan
- Delivery status lives in that platform's execution workflow
- Detailed implementation instructions live in phase files
- Deployment and operations instructions live in deployment docs
- External artifacts live in reference docs

If two documents disagree, resolve them using this precedence:

1. PRD for product intent and scope
2. Build plan for technical architecture
3. Execution workflow for implementation order and current status
4. Phase document for exact execution details of the active task

## Required Vs Optional Documents

Required for almost every project:
- `README.md`
- `[project-name]-prd.md`
- at least one platform build plan
- at least one platform execution workflow
- phase files for active work

Optional depending on project scope:
- `mobile-docs/`
- `web-docs/`
- `backend-docs/`
- deployment platform-specific guides beyond the base runbook/setup files
- `reference-docs/` subfolders that are not needed yet

## Maintenance Rules

- Update the PRD when product scope changes
- Update build plans when architecture decisions change
- Update execution workflows when phase status changes
- Update phase docs while implementing, not after memory has gone stale
- Do not leave placeholder phases linked from a workflow without creating the file
- Remove irrelevant platform folders from small or single-platform projects
