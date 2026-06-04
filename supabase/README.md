# Supabase schema workflow

This folder versions the Supabase database schema for Artemis.

## Current state

- `migrations/20260604114000_initial_remote_schema.sql` is a schema-only snapshot of the current remote database.
- It documents the existing `dev` data pipeline schema, the legacy `public` launch schema, and current dashboard views.
- No launch data, user data, database passwords, or API keys are stored here.
- The local Supabase project is linked to remote project `olcuybolhpccnncaupts` (`Artemis`).
- The initial migration is registered as applied on the remote project, so future migrations can start from this baseline.

## Link the remote project

The Supabase CLI needs an access token before it can link to the hosted project.

```bash
npx supabase login
npx supabase link --project-ref olcuybolhpccnncaupts
```

If the project is already linked, verify it with:

```bash
npx supabase projects list
npx supabase migration list --linked
```

Alternatively:

```bash
export SUPABASE_ACCESS_TOKEN="..."
npx supabase link --project-ref olcuybolhpccnncaupts
```

## Future migrations

Create a new migration for each schema change:

```bash
npx supabase migration new semantic_model_v1
```

After review, apply linked migrations with:

```bash
npx supabase db push --linked
```

Use the SQL editor for manual inspection, but prefer committing schema changes here so the database model stays reproducible.

## Semantic model v1

`migrations/20260604130000_semantic_model_v1.sql` creates the non-destructive `dev_semantic` schema.

Current semantic views:

- `dev_semantic.complete_years`
- `dev_semantic.fact_launches`
- `dev_semantic.dim_years`
- `dev_semantic.dim_agencies`
- `dev_semantic.dim_countries`
- `dev_semantic.dim_statuses`
- `dev_semantic.launch_metrics_by_year`
- `dev_semantic.launch_metrics_by_country`
- `dev_semantic.launch_metrics_by_agency`
- `dev_semantic.ml_launch_features`

The Streamlit app still uses the existing `dev` views. We can migrate dashboard pages to `dev_semantic` progressively.

## Semantic quality v1

`migrations/20260604133000_semantic_quality_v1.sql` adds quality and coverage views:

- `dev_semantic.data_coverage_by_year`
- `dev_semantic.data_quality_summary`
- `dev_semantic.data_quality_by_year`
- `dev_semantic.semantic_health_overview`
- `dev_semantic.backfill_priority_queue`

These views make it explicit which years are complete, which years need audit/backfill, and whether the semantic layer has missing values that could weaken dashboards or machine learning.
