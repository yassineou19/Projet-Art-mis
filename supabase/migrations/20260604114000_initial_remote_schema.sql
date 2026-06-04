


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "dev";


ALTER SCHEMA "dev" OWNER TO "postgres";


CREATE SCHEMA IF NOT EXISTS "public";


ALTER SCHEMA "public" OWNER TO "pg_database_owner";


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
    new.updated_at = now();
    return new;
end;
$$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "dev"."historical_backfill_state" (
    "year" integer NOT NULL,
    "status" "text" DEFAULT 'pending'::"text" NOT NULL,
    "rows_expected" integer,
    "rows_loaded" integer DEFAULT 0 NOT NULL,
    "last_offset" integer DEFAULT 0 NOT NULL,
    "last_error" "text",
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "historical_backfill_state_status_check" CHECK (("status" = ANY (ARRAY['pending'::"text", 'loaded_current'::"text", 'running'::"text", 'complete'::"text", 'rate_limited'::"text", 'failed'::"text"]))),
    CONSTRAINT "historical_backfill_state_year_check" CHECK ((("year" >= 1957) AND ("year" <= 2025)))
);


ALTER TABLE "dev"."historical_backfill_state" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "dev"."ingestion_runs" (
    "id" bigint NOT NULL,
    "started_at" timestamp with time zone DEFAULT "now"(),
    "ended_at" timestamp with time zone,
    "status" "text",
    "rows_raw_upserted" integer DEFAULT 0,
    "rows_clean_upserted" integer DEFAULT 0,
    "error_message" "text",
    "rows_api_received" integer DEFAULT 0,
    "rows_raw_inserted" integer DEFAULT 0,
    "rows_raw_updated" integer DEFAULT 0,
    "rows_clean_inserted" integer DEFAULT 0,
    "rows_clean_updated" integer DEFAULT 0,
    "run_type" "text" DEFAULT 'backfill'::"text"
);


ALTER TABLE "dev"."ingestion_runs" OWNER TO "postgres";


ALTER TABLE "dev"."ingestion_runs" ALTER COLUMN "id" ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME "dev"."ingestion_runs_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);



CREATE TABLE IF NOT EXISTS "dev"."ingestion_state" (
    "pipeline_name" "text" NOT NULL,
    "last_offset" integer DEFAULT 0,
    "last_run_at" timestamp with time zone,
    "last_launch_date" timestamp with time zone,
    "total_rows_ingested" integer DEFAULT 0
);


ALTER TABLE "dev"."ingestion_state" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "dev"."launches_clean" (
    "launch_id" "text" NOT NULL,
    "launch_name" "text",
    "launch_date" timestamp with time zone,
    "launch_year" integer,
    "agency" "text",
    "country" "text",
    "latitude" numeric,
    "longitude" numeric,
    "status" "text",
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "dev"."launches_clean" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."launches_by_country" AS
 SELECT "country",
    "count"(*) AS "launches"
   FROM "dev"."launches_clean"
  WHERE ("country" IS NOT NULL)
  GROUP BY "country"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "dev"."launches_by_country" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."launches_by_year" AS
 SELECT "launch_year" AS "year",
    "count"(*) AS "launches"
   FROM "dev"."launches_clean"
  WHERE ("launch_year" IS NOT NULL)
  GROUP BY "launch_year"
  ORDER BY "launch_year";


ALTER VIEW "dev"."launches_by_year" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."launches_dashboard_detail" AS
 SELECT "launch_year" AS "year",
    "country",
    "agency"
   FROM "dev"."launches_clean"
  WHERE ("launch_year" IS NOT NULL);


ALTER VIEW "dev"."launches_dashboard_detail" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."launches_growth_by_year" AS
 SELECT "year",
    "launches",
    "round"((((("launches" - "lag"("launches") OVER (ORDER BY "year")))::numeric / (NULLIF("lag"("launches") OVER (ORDER BY "year"), 0))::numeric) * (100)::numeric), 2) AS "growth_pct"
   FROM "dev"."launches_by_year";


ALTER VIEW "dev"."launches_growth_by_year" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."launches_map" AS
 SELECT "launch_id",
    "launch_name",
    "launch_year",
    "country",
    "latitude",
    "longitude"
   FROM "dev"."launches_clean"
  WHERE (("latitude" IS NOT NULL) AND ("longitude" IS NOT NULL));


ALTER VIEW "dev"."launches_map" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "dev"."launches_raw" (
    "launch_id" "text" NOT NULL,
    "payload" "jsonb" NOT NULL,
    "source" "text" DEFAULT 'thespacedevs'::"text",
    "ingested_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "dev"."launches_raw" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."space_race_agencies" AS
 SELECT "agency",
    "count"(*) AS "launches",
    "count"(DISTINCT "launch_year") AS "active_years",
    "round"(((("count"(*))::numeric / "sum"("count"(*)) OVER ()) * (100)::numeric), 2) AS "market_share_pct"
   FROM "dev"."launches_clean"
  WHERE ("agency" IS NOT NULL)
  GROUP BY "agency"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "dev"."space_race_agencies" OWNER TO "postgres";


CREATE OR REPLACE VIEW "dev"."top_agencies" AS
 SELECT "agency",
    "count"(*) AS "launches"
   FROM "dev"."launches_clean"
  WHERE ("agency" IS NOT NULL)
  GROUP BY "agency"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "dev"."top_agencies" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."launches_clean" (
    "launch_id" "text",
    "launch_name" "text",
    "launch_date" timestamp without time zone,
    "agency" "text",
    "launch_country" "text",
    "launch_year" numeric
);


ALTER TABLE "public"."launches_clean" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."kpi_total_launches" AS
 SELECT "count"(*) AS "total_launches"
   FROM "public"."launches_clean";


ALTER VIEW "public"."kpi_total_launches" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."launches_by_country" AS
 SELECT "launch_country" AS "country",
    "count"(*) AS "launches",
    "round"(((("count"(*))::numeric * 100.0) / (( SELECT "count"(*) AS "count"
           FROM "public"."launches_clean" "launches_clean_1"))::numeric), 2) AS "percentage"
   FROM "public"."launches_clean"
  GROUP BY "launch_country"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "public"."launches_by_country" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."launches_by_year" AS
 SELECT "launch_year" AS "year",
    "count"(*) AS "launches"
   FROM "public"."launches_clean"
  GROUP BY "launch_year"
  ORDER BY "launch_year";


ALTER VIEW "public"."launches_by_year" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."launches_growth_by_year" AS
 SELECT "launch_year" AS "year",
    "count"(*) AS "launches",
    "lag"("count"(*)) OVER (ORDER BY "launch_year") AS "previous_year_launches",
    COALESCE("round"((((("count"(*) - "lag"("count"(*)) OVER (ORDER BY "launch_year")))::numeric * 100.0) / ("lag"("count"(*)) OVER (ORDER BY "launch_year"))::numeric), 2), (0)::numeric) AS "growth_pct"
   FROM "public"."launches_clean"
  GROUP BY "launch_year"
  ORDER BY "launch_year";


ALTER VIEW "public"."launches_growth_by_year" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."launches_map" AS
 SELECT "launch_name",
    "launch_year",
    "launch_country" AS "country",
        CASE
            WHEN ("launch_country" = 'USA'::"text") THEN 37.0902
            WHEN ("launch_country" = 'Russia'::"text") THEN 61.5240
            WHEN ("launch_country" = 'China'::"text") THEN 35.8617
            WHEN ("launch_country" = 'India'::"text") THEN 20.5937
            WHEN ("launch_country" = 'France'::"text") THEN 46.2276
            ELSE (0)::numeric
        END AS "latitude",
        CASE
            WHEN ("launch_country" = 'USA'::"text") THEN '-95.7129'::numeric
            WHEN ("launch_country" = 'Russia'::"text") THEN 105.3188
            WHEN ("launch_country" = 'China'::"text") THEN 104.1954
            WHEN ("launch_country" = 'India'::"text") THEN 78.9629
            WHEN ("launch_country" = 'France'::"text") THEN 2.2137
            ELSE (0)::numeric
        END AS "longitude"
   FROM "public"."launches_clean";


ALTER VIEW "public"."launches_map" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."launches_raw" (
    "launch_id" "text",
    "launch_name" "text",
    "date" "text",
    "agency" "text",
    "launch_country" "text"
);


ALTER TABLE "public"."launches_raw" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."space_race_agencies" AS
 SELECT "agency",
    "count"(*) AS "launches",
    "min"("launch_year") AS "first_launch_year",
    "max"("launch_year") AS "last_launch_year",
    "count"(DISTINCT "launch_year") AS "active_years",
    "round"(((("count"(*))::numeric * 100.0) / (( SELECT "count"(*) AS "count"
           FROM "public"."launches_clean" "launches_clean_1"))::numeric), 2) AS "market_share_pct"
   FROM "public"."launches_clean"
  WHERE ("agency" IS NOT NULL)
  GROUP BY "agency"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "public"."space_race_agencies" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."subscription_plan_features" (
    "id" bigint NOT NULL,
    "plan_id" "text" NOT NULL,
    "feature" "text" NOT NULL,
    "is_included" boolean DEFAULT true NOT NULL,
    "display_order" integer NOT NULL
);


ALTER TABLE "public"."subscription_plan_features" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."subscription_plan_features_id_seq"
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE "public"."subscription_plan_features_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."subscription_plan_features_id_seq" OWNED BY "public"."subscription_plan_features"."id";



CREATE TABLE IF NOT EXISTS "public"."subscription_plans" (
    "id" "text" NOT NULL,
    "name" "text" NOT NULL,
    "price_monthly_eur" integer NOT NULL,
    "description" "text" NOT NULL,
    "is_active" boolean DEFAULT true NOT NULL,
    "display_order" integer NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "subscription_plans_id_check" CHECK (("id" = ANY (ARRAY['free'::"text", 'pro'::"text", 'premium'::"text"])))
);


ALTER TABLE "public"."subscription_plans" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."top_agencies" AS
 SELECT "agency",
    "count"(*) AS "launches"
   FROM "public"."launches_clean"
  GROUP BY "agency"
  ORDER BY ("count"(*)) DESC;


ALTER VIEW "public"."top_agencies" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."user_profiles" (
    "id" "uuid" NOT NULL,
    "email" "text" NOT NULL,
    "user_type" "text" NOT NULL,
    "subscription_plan" "text" NOT NULL,
    "subscription_status" "text" DEFAULT 'active'::"text" NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    CONSTRAINT "user_profiles_subscription_plan_check" CHECK (("subscription_plan" = ANY (ARRAY['free'::"text", 'pro'::"text", 'premium'::"text"]))),
    CONSTRAINT "user_profiles_user_type_check" CHECK (("user_type" = ANY (ARRAY['space_enthusiast'::"text", 'journalist'::"text"])))
);


ALTER TABLE "public"."user_profiles" OWNER TO "postgres";


ALTER TABLE ONLY "public"."subscription_plan_features" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."subscription_plan_features_id_seq"'::"regclass");



ALTER TABLE ONLY "dev"."historical_backfill_state"
    ADD CONSTRAINT "historical_backfill_state_pkey" PRIMARY KEY ("year");



ALTER TABLE ONLY "dev"."ingestion_runs"
    ADD CONSTRAINT "ingestion_runs_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "dev"."ingestion_state"
    ADD CONSTRAINT "ingestion_state_pkey" PRIMARY KEY ("pipeline_name");



ALTER TABLE ONLY "dev"."launches_clean"
    ADD CONSTRAINT "launches_clean_pkey" PRIMARY KEY ("launch_id");



ALTER TABLE ONLY "dev"."launches_raw"
    ADD CONSTRAINT "launches_raw_pkey" PRIMARY KEY ("launch_id");



ALTER TABLE ONLY "public"."subscription_plan_features"
    ADD CONSTRAINT "subscription_plan_features_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."subscription_plans"
    ADD CONSTRAINT "subscription_plans_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."user_profiles"
    ADD CONSTRAINT "user_profiles_pkey" PRIMARY KEY ("id");



CREATE OR REPLACE TRIGGER "set_user_profiles_updated_at" BEFORE UPDATE ON "public"."user_profiles" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



ALTER TABLE ONLY "public"."subscription_plan_features"
    ADD CONSTRAINT "subscription_plan_features_plan_id_fkey" FOREIGN KEY ("plan_id") REFERENCES "public"."subscription_plans"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."user_profiles"
    ADD CONSTRAINT "user_profiles_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";



GRANT ALL ON TABLE "public"."launches_clean" TO "anon";
GRANT ALL ON TABLE "public"."launches_clean" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_clean" TO "service_role";



GRANT ALL ON TABLE "public"."kpi_total_launches" TO "anon";
GRANT ALL ON TABLE "public"."kpi_total_launches" TO "authenticated";
GRANT ALL ON TABLE "public"."kpi_total_launches" TO "service_role";



GRANT ALL ON TABLE "public"."launches_by_country" TO "anon";
GRANT ALL ON TABLE "public"."launches_by_country" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_by_country" TO "service_role";



GRANT ALL ON TABLE "public"."launches_by_year" TO "anon";
GRANT ALL ON TABLE "public"."launches_by_year" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_by_year" TO "service_role";



GRANT ALL ON TABLE "public"."launches_growth_by_year" TO "anon";
GRANT ALL ON TABLE "public"."launches_growth_by_year" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_growth_by_year" TO "service_role";



GRANT ALL ON TABLE "public"."launches_map" TO "anon";
GRANT ALL ON TABLE "public"."launches_map" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_map" TO "service_role";



GRANT ALL ON TABLE "public"."launches_raw" TO "anon";
GRANT ALL ON TABLE "public"."launches_raw" TO "authenticated";
GRANT ALL ON TABLE "public"."launches_raw" TO "service_role";



GRANT ALL ON TABLE "public"."space_race_agencies" TO "anon";
GRANT ALL ON TABLE "public"."space_race_agencies" TO "authenticated";
GRANT ALL ON TABLE "public"."space_race_agencies" TO "service_role";



GRANT ALL ON TABLE "public"."subscription_plan_features" TO "anon";
GRANT ALL ON TABLE "public"."subscription_plan_features" TO "authenticated";
GRANT ALL ON TABLE "public"."subscription_plan_features" TO "service_role";



GRANT ALL ON SEQUENCE "public"."subscription_plan_features_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."subscription_plan_features_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."subscription_plan_features_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."subscription_plans" TO "anon";
GRANT ALL ON TABLE "public"."subscription_plans" TO "authenticated";
GRANT ALL ON TABLE "public"."subscription_plans" TO "service_role";



GRANT ALL ON TABLE "public"."top_agencies" TO "anon";
GRANT ALL ON TABLE "public"."top_agencies" TO "authenticated";
GRANT ALL ON TABLE "public"."top_agencies" TO "service_role";



GRANT ALL ON TABLE "public"."user_profiles" TO "anon";
GRANT ALL ON TABLE "public"."user_profiles" TO "authenticated";
GRANT ALL ON TABLE "public"."user_profiles" TO "service_role";



ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";







