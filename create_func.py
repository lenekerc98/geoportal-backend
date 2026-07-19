import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

sql = """
CREATE OR REPLACE FUNCTION catastro.calcular_rumbo(p1 geometry, p2 geometry)
RETURNS text AS $$
DECLARE
    azimuth_rad float;
    azimuth_deg float;
    d int;
    m int;
    s float;
    quadrant text;
    rumbo_deg float;
BEGIN
    azimuth_rad := ST_Azimuth(p1, p2);
    IF azimuth_rad IS NULL THEN RETURN NULL; END IF;
    
    azimuth_deg := degrees(azimuth_rad);
    
    -- Para Rumbo topográfico (Cuadrantes: NE, SE, SW, NW)
    IF azimuth_deg >= 0 AND azimuth_deg <= 90 THEN
        quadrant := 'NE';
        rumbo_deg := azimuth_deg;
    ELSIF azimuth_deg > 90 AND azimuth_deg <= 180 THEN
        quadrant := 'SE';
        rumbo_deg := 180 - azimuth_deg;
    ELSIF azimuth_deg > 180 AND azimuth_deg <= 270 THEN
        quadrant := 'SW';
        rumbo_deg := azimuth_deg - 180;
    ELSE
        quadrant := 'NW';
        rumbo_deg := 360 - azimuth_deg;
    END IF;

    d := floor(rumbo_deg);
    m := floor((rumbo_deg - d) * 60);
    s := ((rumbo_deg - d) * 60 - m) * 60;
    
    -- Formato: N 45° 30' 15.2" E  o S ...
    IF quadrant = 'NE' THEN
        RETURN 'N ' || d::text || '° ' || m::text || ''' ' || round(s::numeric, 1)::text || '" E';
    ELSIF quadrant = 'SE' THEN
        RETURN 'S ' || d::text || '° ' || m::text || ''' ' || round(s::numeric, 1)::text || '" E';
    ELSIF quadrant = 'SW' THEN
        RETURN 'S ' || d::text || '° ' || m::text || ''' ' || round(s::numeric, 1)::text || '" W';
    ELSE
        RETURN 'N ' || d::text || '° ' || m::text || ''' ' || round(s::numeric, 1)::text || '" W';
    END IF;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
"""

try:
    with engine.begin() as conn:
        conn.execute(text(sql))
        print("Function created successfully!")
except Exception as e:
    print("Error:", e)
