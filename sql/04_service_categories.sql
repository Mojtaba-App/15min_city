DROP TABLE IF EXISTS service_categories;

CREATE TABLE service_categories AS
SELECT
    gid,
    service_ty,
    nearest_vertex,
    CASE
        WHEN LOWER(service_ty) LIKE '%school%'
          OR LOWER(service_ty) LIKE '%education%'
          OR service_ty LIKE '%مدرسه%'
          OR service_ty LIKE '%آموزش%'
          OR service_ty LIKE '%دانشگاه%'
          OR service_ty LIKE '%مهد%'
        THEN 'education'

        WHEN LOWER(service_ty) LIKE '%hospital%'
          OR LOWER(service_ty) LIKE '%clinic%'
          OR LOWER(service_ty) LIKE '%health%'
          OR LOWER(service_ty) LIKE '%pharmacy%'
          OR service_ty LIKE '%بیمارستان%'
          OR service_ty LIKE '%درمان%'
          OR service_ty LIKE '%کلینیک%'
          OR service_ty LIKE '%داروخانه%'
          OR service_ty LIKE '%سلامت%'
        THEN 'health'

        WHEN LOWER(service_ty) LIKE '%shop%'
          OR LOWER(service_ty) LIKE '%market%'
          OR LOWER(service_ty) LIKE '%store%'
          OR LOWER(service_ty) LIKE '%mall%'
          OR service_ty LIKE '%فروشگاه%'
          OR service_ty LIKE '%بازار%'
          OR service_ty LIKE '%سوپر%'
          OR service_ty LIKE '%مرکز خرید%'
          OR service_ty LIKE '%مغازه%'
        THEN 'shopping'

        WHEN LOWER(service_ty) LIKE '%park%'
          OR LOWER(service_ty) LIKE '%sport%'
          OR LOWER(service_ty) LIKE '%recreation%'
          OR LOWER(service_ty) LIKE '%gym%'
          OR service_ty LIKE '%پارک%'
          OR service_ty LIKE '%ورزش%'
          OR service_ty LIKE '%تفریح%'
          OR service_ty LIKE '%باشگاه%'
          OR service_ty LIKE '%فضای سبز%'
        THEN 'recreation'

        ELSE 'other'
    END AS category
FROM urban_services
WHERE nearest_vertex IS NOT NULL
  AND service_ty IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_service_categories_gid
ON service_categories(gid);

CREATE INDEX IF NOT EXISTS idx_service_categories_category
ON service_categories(category);

CREATE INDEX IF NOT EXISTS idx_service_categories_nearest_vertex
ON service_categories(nearest_vertex);

ANALYZE service_categories;
