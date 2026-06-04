create or replace view dev_semantic.data_coverage_by_year as
select
    y.year,
    y.backfill_status,
    y.rows_loaded,
    y.rows_expected,
    case
        when y.rows_expected is null then null
        when y.rows_expected = 0 then 100.00
        else round(100.0 * y.rows_loaded / nullif(y.rows_expected, 0), 2)
    end as coverage_pct,
    y.is_complete,
    y.has_launch_data,
    case
        when y.is_complete then 'complete'
        when y.rows_expected is null and y.has_launch_data then 'audit_needed'
        when y.rows_expected is null then 'unknown'
        when y.rows_loaded = 0 then 'missing'
        when y.rows_loaded < y.rows_expected then 'partial'
        else 'review'
    end as coverage_category,
    case
        when y.is_complete then 0
        when y.rows_expected is null and y.has_launch_data then 20
        when y.rows_expected is null then 30
        when y.rows_loaded = 0 then 10
        when y.rows_loaded < y.rows_expected then 5
        else 25
    end as backfill_priority,
    case
        when y.is_complete then 0
        when y.rows_expected is null then null
        else greatest(y.rows_expected - y.rows_loaded, 0)
    end as rows_missing,
    y.backfill_updated_at
from dev_semantic.dim_years y
order by y.year;

comment on view dev_semantic.data_coverage_by_year is
    'Year-level historical coverage health. Used to decide whether analytics and ML can trust a period.';

create or replace view dev_semantic.data_quality_summary as
with base as (
    select *
    from dev_semantic.fact_launches
),
checks as (
    select
        count(*) as total_launches,
        count(*) filter (where launch_id is null or launch_id = '') as missing_launch_id,
        count(*) filter (where launch_name is null or launch_name = '') as missing_launch_name,
        count(*) filter (where launch_date is null) as missing_launch_date,
        count(*) filter (where launch_year is null) as missing_launch_year,
        count(*) filter (where agency_name is null or agency_name = '' or agency_name = 'UNKNOWN') as missing_agency,
        count(*) filter (where launch_country is null or launch_country = '' or launch_country = 'UNKNOWN') as missing_country,
        count(*) filter (where latitude is null or longitude is null) as missing_coordinates,
        count(*) filter (where status_name is null or status_name = '') as missing_status,
        count(*) filter (where status_category = 'other') as other_status_category,
        count(*) filter (where not is_complete_year) as launches_outside_complete_years,
        count(distinct launch_year) as years_with_launches,
        count(distinct agency_name) as agencies,
        count(distinct launch_country) as countries
    from base
)
select
    total_launches,
    missing_launch_id,
    missing_launch_name,
    missing_launch_date,
    missing_launch_year,
    missing_agency,
    missing_country,
    missing_coordinates,
    missing_status,
    other_status_category,
    launches_outside_complete_years,
    years_with_launches,
    agencies,
    countries,
    round(100.0 * missing_coordinates / nullif(total_launches, 0), 2) as missing_coordinates_pct,
    round(100.0 * launches_outside_complete_years / nullif(total_launches, 0), 2) as launches_outside_complete_years_pct
from checks;

comment on view dev_semantic.data_quality_summary is
    'Global data quality indicators for launch analytics.';

create or replace view dev_semantic.data_quality_by_year as
select
    launch_year as year,
    count(*) as launches,
    count(*) filter (where is_complete_year) as launches_in_complete_years,
    count(*) filter (where agency_name is null or agency_name = '' or agency_name = 'UNKNOWN') as missing_agency,
    count(*) filter (where launch_country is null or launch_country = '' or launch_country = 'UNKNOWN') as missing_country,
    count(*) filter (where latitude is null or longitude is null) as missing_coordinates,
    count(*) filter (where status_name is null or status_name = '') as missing_status,
    count(*) filter (where status_category = 'other') as other_status_category,
    round(
        100.0 * count(*) filter (where latitude is null or longitude is null) / nullif(count(*), 0),
        2
    ) as missing_coordinates_pct,
    bool_or(is_complete_year) as is_complete_year
from dev_semantic.fact_launches
where launch_year is not null
group by launch_year
order by launch_year;

comment on view dev_semantic.data_quality_by_year is
    'Year-level data quality indicators.';

create or replace view dev_semantic.semantic_health_overview as
select
    (select count(*) from dev_semantic.complete_years) as complete_years,
    (select count(*) from dev_semantic.dim_years where backfill_status = 'loaded_current') as years_loaded_not_audited,
    (select count(*) from dev_semantic.dim_years where backfill_status = 'pending') as pending_years,
    (select count(*) from dev_semantic.fact_launches) as total_launches,
    (select count(*) from dev_semantic.fact_launches where is_complete_year) as launches_in_complete_years,
    (
        select count(*)
        from dev_semantic.data_coverage_by_year
        where coverage_category in ('missing', 'partial', 'audit_needed')
    ) as years_requiring_action,
    (
        select missing_coordinates
        from dev_semantic.data_quality_summary
    ) as launches_missing_coordinates,
    (
        select other_status_category
        from dev_semantic.data_quality_summary
    ) as launches_with_other_status_category;

comment on view dev_semantic.semantic_health_overview is
    'One-row health overview for the semantic layer.';

create or replace view dev_semantic.backfill_priority_queue as
select
    year,
    backfill_status,
    coverage_category,
    backfill_priority,
    rows_loaded,
    rows_expected,
    rows_missing,
    coverage_pct,
    backfill_updated_at
from dev_semantic.data_coverage_by_year
where coverage_category <> 'complete'
order by backfill_priority asc, year asc;

comment on view dev_semantic.backfill_priority_queue is
    'Prioritized year queue for historical audit and backfill.';

grant select on all tables in schema dev_semantic to anon, authenticated, service_role;
