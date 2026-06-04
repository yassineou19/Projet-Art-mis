create schema if not exists dev_semantic;

comment on schema dev_semantic is
    'Semantic analytics layer for Artemis dashboards and machine learning.';

create or replace view dev_semantic.complete_years as
select
    year,
    rows_loaded,
    rows_expected,
    updated_at as coverage_checked_at
from dev.historical_backfill_state
where status = 'complete'
  and rows_expected is not null
  and rows_loaded >= rows_expected;

comment on view dev_semantic.complete_years is
    'Years audited as complete by the historical backfill process.';

create or replace view dev_semantic.fact_launches as
select
    l.launch_id,
    l.launch_name,
    l.launch_date,
    l.launch_year,
    l.agency as agency_name,
    l.country as launch_country,
    l.latitude,
    l.longitude,
    l.status as status_name,
    case
        when l.status ilike '%successful%' then 'success'
        when l.status ilike '%partial%' then 'partial_failure'
        when l.status ilike '%failure%' then 'failure'
        when l.status ilike '%go for launch%' then 'scheduled'
        when l.status ilike '%to be%' then 'uncertain'
        else 'other'
    end as status_category,
    (l.status ilike '%successful%') as is_success,
    (
        l.status ilike '%failure%'
        and l.status not ilike '%partial%'
    ) as is_failure,
    (cy.year is not null) as is_complete_year,
    l.updated_at
from dev.launches_clean l
left join dev_semantic.complete_years cy
    on cy.year = l.launch_year;

comment on view dev_semantic.fact_launches is
    'Canonical launch fact view. One row per launch, with normalized semantic fields.';

create or replace view dev_semantic.dim_years as
select
    y.year,
    coalesce(h.status, 'not_loaded') as backfill_status,
    coalesce(h.rows_loaded, 0) as rows_loaded,
    h.rows_expected,
    (cy.year is not null) as is_complete,
    (coalesce(h.rows_loaded, 0) > 0) as has_launch_data,
    h.updated_at as backfill_updated_at
from generate_series(1957, 2025) as y(year)
left join dev.historical_backfill_state h
    on h.year = y.year
left join dev_semantic.complete_years cy
    on cy.year = y.year;

comment on view dev_semantic.dim_years is
    'Year dimension with historical coverage status.';

create or replace view dev_semantic.dim_agencies as
select
    md5(coalesce(agency_name, 'UNKNOWN')) as agency_key,
    coalesce(agency_name, 'UNKNOWN') as agency_name,
    count(*) as launches,
    count(*) filter (where is_complete_year) as launches_in_complete_years,
    min(launch_year) as first_launch_year,
    max(launch_year) as last_launch_year,
    count(distinct launch_year) as active_years,
    count(distinct launch_country) as countries_used,
    count(*) filter (where is_success) as successful_launches,
    count(*) filter (where is_failure) as failed_launches
from dev_semantic.fact_launches
group by coalesce(agency_name, 'UNKNOWN');

comment on view dev_semantic.dim_agencies is
    'Agency dimension derived from launch provider names.';

create or replace view dev_semantic.dim_countries as
select
    md5(coalesce(launch_country, 'UNKNOWN')) as country_key,
    coalesce(launch_country, 'UNKNOWN') as country_name,
    count(*) as launches,
    count(*) filter (where is_complete_year) as launches_in_complete_years,
    min(launch_year) as first_launch_year,
    max(launch_year) as last_launch_year,
    count(distinct agency_name) as agencies,
    count(*) filter (where is_success) as successful_launches,
    count(*) filter (where is_failure) as failed_launches
from dev_semantic.fact_launches
group by coalesce(launch_country, 'UNKNOWN');

comment on view dev_semantic.dim_countries is
    'Launch country/location dimension derived from launch pad location names.';

create or replace view dev_semantic.dim_statuses as
select
    md5(coalesce(status_name, 'UNKNOWN')) as status_key,
    coalesce(status_name, 'UNKNOWN') as status_name,
    status_category,
    count(*) as launches
from dev_semantic.fact_launches
group by coalesce(status_name, 'UNKNOWN'), status_category;

comment on view dev_semantic.dim_statuses is
    'Launch status dimension with normalized status categories.';

create or replace view dev_semantic.launch_metrics_by_year as
select
    launch_year as year,
    count(*) as launches,
    count(*) filter (where is_success) as successful_launches,
    count(*) filter (where is_failure) as failed_launches,
    count(*) filter (where status_category = 'partial_failure') as partial_failures,
    count(*) filter (where status_category in ('scheduled', 'uncertain')) as uncertain_or_scheduled_launches,
    count(distinct agency_name) as active_agencies,
    count(distinct launch_country) as active_countries,
    round(
        100.0 * count(*) filter (where is_success) / nullif(count(*), 0),
        2
    ) as success_rate_pct,
    bool_or(is_complete_year) as is_complete_year
from dev_semantic.fact_launches
where launch_year is not null
group by launch_year
order by launch_year;

comment on view dev_semantic.launch_metrics_by_year is
    'Annual launch metrics for analytics, with completion flag.';

create or replace view dev_semantic.launch_metrics_by_country as
select
    launch_country as country,
    count(*) as launches,
    count(*) filter (where is_complete_year) as launches_in_complete_years,
    count(distinct launch_year) as active_years,
    count(distinct agency_name) as agencies,
    count(*) filter (where is_success) as successful_launches,
    count(*) filter (where is_failure) as failed_launches,
    round(
        100.0 * count(*) / nullif(sum(count(*)) over (), 0),
        2
    ) as market_share_pct
from dev_semantic.fact_launches
where launch_country is not null
group by launch_country
order by count(*) desc;

comment on view dev_semantic.launch_metrics_by_country is
    'Country-level launch metrics for dashboard and semantic analytics.';

create or replace view dev_semantic.launch_metrics_by_agency as
select
    agency_name,
    count(*) as launches,
    count(*) filter (where is_complete_year) as launches_in_complete_years,
    count(distinct launch_year) as active_years,
    count(distinct launch_country) as countries_used,
    count(*) filter (where is_success) as successful_launches,
    count(*) filter (where is_failure) as failed_launches,
    round(
        100.0 * count(*) / nullif(sum(count(*)) over (), 0),
        2
    ) as market_share_pct
from dev_semantic.fact_launches
where agency_name is not null
group by agency_name
order by count(*) desc;

comment on view dev_semantic.launch_metrics_by_agency is
    'Agency-level launch metrics for dashboard and semantic analytics.';

create or replace view dev_semantic.ml_launch_features as
with yearly as (
    select
        year,
        launches,
        successful_launches,
        failed_launches,
        partial_failures,
        active_agencies,
        active_countries,
        success_rate_pct
    from dev_semantic.launch_metrics_by_year
    where is_complete_year
)
select
    year,
    launches,
    lag(launches) over (order by year) as previous_year_launches,
    launches - lag(launches) over (order by year) as launches_delta_previous_year,
    round(
        100.0 * (launches - lag(launches) over (order by year))
        / nullif(lag(launches) over (order by year), 0),
        2
    ) as launches_growth_pct,
    successful_launches,
    failed_launches,
    partial_failures,
    active_agencies,
    active_countries,
    success_rate_pct,
    lead(launches) over (order by year) as target_next_year_launches
from yearly
order by year;

comment on view dev_semantic.ml_launch_features is
    'ML-ready yearly feature view restricted to audited complete years. target_next_year_launches is included for supervised forecasting experiments.';

grant usage on schema dev_semantic to anon, authenticated, service_role;
grant select on all tables in schema dev_semantic to anon, authenticated, service_role;
