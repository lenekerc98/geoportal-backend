--
-- PostgreSQL database dump
--

\restrict ao4DFTUrEnMt6FLDjpeIeMmh3ZhVhShYGxGQZvPoRT9NLjEfsmxV1wd3Omw0DJ3

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: catastro; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA catastro;


--
-- Name: interoperabilidad; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA interoperabilidad;


--
-- Name: seguridad; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA seguridad;


--
-- Name: calcular_rumbo(public.geometry, public.geometry); Type: FUNCTION; Schema: catastro; Owner: -
--

CREATE FUNCTION catastro.calcular_rumbo(p1 public.geometry, p2 public.geometry) RETURNS text
    LANGUAGE plpgsql IMMUTABLE
    AS $$
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
        RETURN 'N ' || d::text || '° ' || m::text || ''' ' || round(s::numeric)::text || '" E';
    ELSIF quadrant = 'SE' THEN
        RETURN 'S ' || d::text || '° ' || m::text || ''' ' || round(s::numeric)::text || '" E';
    ELSIF quadrant = 'SW' THEN
        RETURN 'S ' || d::text || '° ' || m::text || ''' ' || round(s::numeric)::text || '" W';
    ELSE
        RETURN 'N ' || d::text || '° ' || m::text || ''' ' || round(s::numeric)::text || '" W';
    END IF;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: cantones; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.cantones (
    id integer NOT NULL,
    codigo_dpa character varying(4) NOT NULL,
    id_provincia integer,
    nombre character varying(100) NOT NULL,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: cantones_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.cantones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cantones_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.cantones_id_seq OWNED BY catastro.cantones.id;


--
-- Name: capa_dibujo; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.capa_dibujo (
    id integer NOT NULL,
    tipo character varying(50) NOT NULL,
    geom public.geometry(Geometry,32717),
    usuario_id integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: capa_dibujo_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.capa_dibujo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: capa_dibujo_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.capa_dibujo_id_seq OWNED BY catastro.capa_dibujo.id;


--
-- Name: capas_adicionales; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.capas_adicionales (
    id integer NOT NULL,
    nombre_capa character varying(255) NOT NULL,
    tabla_db character varying(100) NOT NULL,
    tipo_geometria character varying(50),
    empresa_id integer,
    fecha_subida timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    tipo_capa character varying(50) DEFAULT 'adicional'::character varying,
    color character varying(20) DEFAULT '#a855f7'::character varying,
    opacidad numeric(3,2) DEFAULT 0.35,
    borde_color character varying(20) DEFAULT '#7e22ce'::character varying,
    borde_grosor integer DEFAULT 2
);


--
-- Name: capas_adicionales_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.capas_adicionales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: capas_adicionales_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.capas_adicionales_id_seq OWNED BY catastro.capas_adicionales.id;


--
-- Name: capas_cad_cartas; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.capas_cad_cartas (
    id integer NOT NULL,
    nombre_archivo character varying(255) NOT NULL,
    formato_origen character varying(20) DEFAULT 'CAD'::character varying,
    capa_cad character varying(100) NOT NULL,
    tipo_geometria character varying(50),
    texto character varying(500),
    color character varying(30),
    geom public.geometry(Geometry,32717),
    propiedades jsonb DEFAULT '{}'::jsonb,
    fecha_subida timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: capas_cad_cartas_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.capas_cad_cartas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: capas_cad_cartas_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.capas_cad_cartas_id_seq OWNED BY catastro.capas_cad_cartas.id;


--
-- Name: cartas_topograficas; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.cartas_topograficas (
    id integer NOT NULL,
    codigo character varying(255) NOT NULL,
    nombre character varying(255) NOT NULL,
    cuadricula character varying(255) DEFAULT 'ZONA 17S'::character varying,
    escala character varying(50) DEFAULT '1:50000'::character varying,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    nombre_archivo character varying(255)
);


--
-- Name: cartas_topograficas_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.cartas_topograficas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cartas_topograficas_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.cartas_topograficas_id_seq OWNED BY catastro.cartas_topograficas.id;


--
-- Name: ciudades; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.ciudades (
    id integer NOT NULL,
    codigo_dpa character varying(6) NOT NULL,
    id_canton integer,
    nombre character varying(100) NOT NULL,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: ciudades_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.ciudades_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ciudades_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.ciudades_id_seq OWNED BY catastro.ciudades.id;


--
-- Name: codigo_catastral; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.codigo_catastral (
    codigo character varying(100) NOT NULL,
    activo boolean DEFAULT true,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    posesionario_id integer,
    empresa_id integer
);


--
-- Name: elementos_adicionales; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.elementos_adicionales (
    id integer NOT NULL,
    capa_id integer,
    geom public.geometry,
    propiedades jsonb
);


--
-- Name: elementos_adicionales_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.elementos_adicionales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: elementos_adicionales_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.elementos_adicionales_id_seq OWNED BY catastro.elementos_adicionales.id;


--
-- Name: empresa; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.empresa (
    id integer NOT NULL,
    ruc character varying(20),
    nombre character varying(255) NOT NULL,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    telefono character varying(50),
    correo character varying(100),
    direccion text,
    parametros jsonb DEFAULT '{}'::jsonb,
    provincia character varying(100),
    canton character varying(100),
    ciudad character varying(100),
    sector character varying(50),
    logo_url text,
    nombre_alcalde character varying(200),
    nombre_director character varying(200),
    sbu_actual numeric(10,2),
    valor_m2_urbano numeric(10,2),
    valor_m2_rural numeric(10,2),
    proyecto_id integer,
    bandera_url text
);


--
-- Name: empresa_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.empresa_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: empresa_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.empresa_id_seq OWNED BY catastro.empresa.id;


--
-- Name: empresa_proyecto; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.empresa_proyecto (
    empresa_id integer NOT NULL,
    proyecto_id integer NOT NULL
);


--
-- Name: linea_lindero; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.linea_lindero (
    id integer NOT NULL,
    predio_id integer,
    longitud numeric(14,2),
    rumbo character varying(100),
    colindante character varying(255),
    geom public.geometry(LineString,32717),
    cod_catastral character varying(100),
    tramo character varying(20),
    estado character varying(20) DEFAULT 'Activo'::character varying,
    fecha_creacion date DEFAULT CURRENT_DATE,
    fecha_baja date,
    empresa_id integer
);


--
-- Name: linea_lindero_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.linea_lindero_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: linea_lindero_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.linea_lindero_id_seq OWNED BY catastro.linea_lindero.id;


--
-- Name: ortofotos_catalogo; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.ortofotos_catalogo (
    id integer NOT NULL,
    nombre_archivo character varying(255) NOT NULL,
    ruta_completa character varying(1024) NOT NULL,
    srid_original integer,
    geom public.geometry(Polygon,32717),
    tipo_archivo character varying(10),
    id_provincia integer,
    id_canton integer,
    id_ciudad integer,
    empresa_id integer,
    proyecto_id integer
);


--
-- Name: ortofotos_catalogo_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.ortofotos_catalogo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ortofotos_catalogo_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.ortofotos_catalogo_id_seq OWNED BY catastro.ortofotos_catalogo.id;


--
-- Name: posesionario; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.posesionario (
    id integer NOT NULL,
    cedula character varying(50),
    nombre character varying(255) NOT NULL,
    empresa_id integer,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: posesionario_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.posesionario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: posesionario_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.posesionario_id_seq OWNED BY catastro.posesionario.id;


--
-- Name: predio; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.predio (
    id integer NOT NULL,
    cod_catastral character varying(100),
    posesionario_id integer,
    area_ha numeric(14,4),
    geom public.geometry(Polygon,32717),
    estado character varying(20) DEFAULT 'Activo'::character varying,
    fecha_creacion date DEFAULT CURRENT_DATE,
    fecha_baja date,
    predio_padre_id integer,
    empresa_id integer,
    id_provincia integer,
    id_canton integer,
    id_ciudad integer,
    proyecto_id integer,
    creado_por integer,
    modificado_por integer,
    fecha_modificacion timestamp without time zone,
    angulo_texto numeric(5,2) DEFAULT 0,
    codigo_carta character varying(50),
    nombre_carta character varying(100),
    cuadricula_carta character varying(50),
    fecha_adjudicacion character varying(50),
    numero_tramite character varying(100),
    institucion character varying(255),
    operador_temporal_id integer,
    tipo_creador character varying(20) DEFAULT 'REGISTRADO'::character varying,
    creador_nombre character varying(150),
    sector character varying(150),
    parroquia character varying(100),
    codigo_anterior character varying(100)
);


--
-- Name: predio_historial; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.predio_historial (
    id integer NOT NULL,
    predio_id integer,
    area_ha numeric(14,4),
    geom public.geometry(Polygon,32717),
    modificado_por integer,
    observacion text,
    fecha_registro timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: predio_historial_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.predio_historial_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: predio_historial_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.predio_historial_id_seq OWNED BY catastro.predio_historial.id;


--
-- Name: predio_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.predio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: predio_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.predio_id_seq OWNED BY catastro.predio.id;


--
-- Name: provincias; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.provincias (
    id integer NOT NULL,
    codigo_dpa character varying(2) NOT NULL,
    nombre character varying(100) NOT NULL
);


--
-- Name: provincias_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.provincias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: provincias_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.provincias_id_seq OWNED BY catastro.provincias.id;


--
-- Name: proyecto; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.proyecto (
    id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    descripcion text,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    empresa_id integer,
    estado character varying(50) DEFAULT 'Activo'::character varying,
    map_lat numeric(15,8) DEFAULT '-1.5833'::numeric,
    map_lng numeric(15,8) DEFAULT '-79.4667'::numeric,
    map_zoom integer DEFAULT 14,
    map_basemap character varying(100) DEFAULT 'osm'::character varying
);


--
-- Name: proyecto_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.proyecto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: proyecto_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.proyecto_id_seq OWNED BY catastro.proyecto.id;


--
-- Name: shape_00257a6d; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.shape_00257a6d (
    id integer NOT NULL,
    objectid numeric(9,0),
    tipo_trami character varying(50),
    numero_tra character varying(15),
    institucio character varying(22),
    numero_pro character varying(15),
    fecha_adju date,
    nombre_pro character varying(250),
    numero_ide character varying(13),
    nacionalid character varying(20),
    estado_civ character varying(15),
    nombre_p_1 character varying(250),
    numero_i_1 character varying(13),
    nacional_1 character varying(20),
    estado_c_1 character varying(20),
    tipo_propi character varying(20),
    forma_adqu character varying(20),
    infraestru character varying(150),
    uso_suelo_ character varying(50),
    provincia character varying(50),
    canton character varying(50),
    parroquia character varying(50),
    sector character varying(50),
    clave_cata character varying(40),
    superficie numeric(19,11),
    centroide_ numeric(19,11),
    centroide1 numeric(19,11),
    analista_s character varying(50),
    observacio character varying(254),
    shape_leng numeric(19,11),
    shape_area numeric(19,11),
    expediente character varying(6),
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: shape_00257a6d_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.shape_00257a6d_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shape_00257a6d_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.shape_00257a6d_id_seq OWNED BY catastro.shape_00257a6d.id;


--
-- Name: shape_e9f98d32; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.shape_e9f98d32 (
    id integer NOT NULL,
    objectid numeric(9,0),
    tipo_trami character varying(50),
    numero_tra character varying(15),
    institucio character varying(22),
    numero_pro character varying(15),
    fecha_adju date,
    nombre_pro character varying(250),
    numero_ide character varying(13),
    nacionalid character varying(20),
    estado_civ character varying(15),
    nombre_p_1 character varying(250),
    numero_i_1 character varying(13),
    nacional_1 character varying(20),
    estado_c_1 character varying(20),
    tipo_propi character varying(20),
    forma_adqu character varying(20),
    infraestru character varying(150),
    uso_suelo_ character varying(50),
    provincia character varying(50),
    canton character varying(50),
    parroquia character varying(50),
    sector character varying(50),
    clave_cata character varying(40),
    superficie numeric(19,11),
    centroide_ numeric(19,11),
    centroide1 numeric(19,11),
    analista_s character varying(50),
    observacio character varying(254),
    shape_leng numeric(19,11),
    shape_area numeric(19,11),
    expediente character varying(6),
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: shape_e9f98d32_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.shape_e9f98d32_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: shape_e9f98d32_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.shape_e9f98d32_id_seq OWNED BY catastro.shape_e9f98d32.id;


--
-- Name: stg_0463eaf7; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_0463eaf7 (
    id integer NOT NULL,
    objectid integer,
    tipo_trami character varying,
    numero_tra character varying,
    institucio character varying,
    numero_pro character varying,
    fecha_adju date,
    nombre_pro character varying,
    numero_ide character varying,
    nacionalid character varying,
    estado_civ character varying,
    nombre_p_1 character varying,
    numero_i_1 character varying,
    nacional_1 character varying,
    estado_c_1 character varying,
    tipo_propi character varying,
    forma_adqu character varying,
    infraestru character varying,
    uso_suelo_ character varying,
    provincia character varying,
    canton character varying,
    parroquia character varying,
    sector character varying,
    clave_cata character varying,
    superficie double precision,
    centroide_ double precision,
    centroide1 double precision,
    analista_s character varying,
    observacio character varying,
    shape_leng double precision,
    shape_area double precision,
    expediente character varying,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_0463eaf7_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_0463eaf7_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_0463eaf7_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_0463eaf7_id_seq OWNED BY catastro.stg_0463eaf7.id;


--
-- Name: stg_24174c69; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_24174c69 (
    ogc_fid integer NOT NULL,
    altitude character varying,
    analista_s character varying,
    apellidos character varying,
    area character varying,
    area_ha double precision,
    area_m2 bigint,
    a_o integer,
    begin character varying,
    canton character varying,
    categories character varying,
    cde_ruc character varying,
    cdi_ruc character varying,
    cedula bigint,
    ced_ruc character varying,
    centroide double precision,
    centroide1 double precision,
    city character varying,
    cod_cat character varying,
    color integer,
    color_1 character varying,
    correo character varying,
    date_modif character varying,
    datos character varying,
    descrip character varying,
    descriptio character varying,
    displaymod character varying,
    dist double precision,
    elevation character varying,
    "end" character varying,
    entity character varying,
    estado_civ character varying,
    estado_c_1 character varying,
    este character varying,
    expediente character varying,
    fecha_adju date,
    fid bigint,
    forma_adqu character varying,
    ha bigint,
    id bigint,
    id_1 double precision,
    infraestru character varying,
    institucio character varying,
    layer character varying,
    linetype character varying,
    linewt integer,
    link character varying,
    lote bigint,
    manzana bigint,
    med double precision,
    medidas double precision,
    nacionalid character varying,
    nacional_1 character varying,
    name bigint,
    nombres character varying,
    nombre_pro character varying,
    nombre_p_1 character varying,
    nom_predio character varying,
    nom_previo character varying,
    norte character varying,
    numero_ide character varying,
    numero_i_1 character varying,
    numero_pro character varying,
    numero_tra character varying,
    num_lote integer,
    num_manz integer,
    num_maz integer,
    num_pred integer,
    num_predio integer,
    objectid integer,
    observ character varying,
    observacio character varying,
    oeste character varying,
    origen_shp character varying,
    parroquia character varying,
    path character varying,
    "position" character varying,
    predio bigint,
    propietrio character varying,
    provincia character varying,
    recinto character varying,
    rect character varying,
    refname character varying,
    sector character varying,
    shape_area double precision,
    shape_leng double precision,
    superficie double precision,
    sur character varying,
    symbol character varying,
    telef character varying,
    telefono bigint,
    telf character varying,
    tipo_propi character varying,
    tipo_trami character varying,
    type character varying,
    uso_suelo character varying,
    visible bigint,
    xcentroide double precision,
    ycentroide double precision,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_24174c69_ogc_fid_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_24174c69_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_24174c69_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_24174c69_ogc_fid_seq OWNED BY catastro.stg_24174c69.ogc_fid;


--
-- Name: stg_445a66d3; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_445a66d3 (
    id integer NOT NULL,
    objectid integer,
    tipo_trami character varying,
    numero_tra character varying,
    institucio character varying,
    numero_pro character varying,
    fecha_adju date,
    nombre_pro character varying,
    numero_ide character varying,
    nacionalid character varying,
    estado_civ character varying,
    nombre_p_1 character varying,
    numero_i_1 character varying,
    nacional_1 character varying,
    estado_c_1 character varying,
    tipo_propi character varying,
    forma_adqu character varying,
    infraestru character varying,
    uso_suelo_ character varying,
    provincia character varying,
    canton character varying,
    parroquia character varying,
    sector character varying,
    clave_cata character varying,
    superficie double precision,
    centroide_ double precision,
    centroide1 double precision,
    analista_s character varying,
    observacio character varying,
    shape_leng double precision,
    shape_area double precision,
    expediente character varying,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_445a66d3_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_445a66d3_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_445a66d3_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_445a66d3_id_seq OWNED BY catastro.stg_445a66d3.id;


--
-- Name: stg_7d469576; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_7d469576 (
    id integer NOT NULL,
    objectid integer,
    tipo_trami character varying,
    numero_tra character varying,
    institucio character varying,
    numero_pro character varying,
    fecha_adju date,
    nombre_pro character varying,
    numero_ide character varying,
    nacionalid character varying,
    estado_civ character varying,
    nombre_p_1 character varying,
    numero_i_1 character varying,
    nacional_1 character varying,
    estado_c_1 character varying,
    tipo_propi character varying,
    forma_adqu character varying,
    infraestru character varying,
    uso_suelo_ character varying,
    provincia character varying,
    canton character varying,
    parroquia character varying,
    sector character varying,
    clave_cata character varying,
    superficie double precision,
    centroide_ double precision,
    centroide1 double precision,
    analista_s character varying,
    observacio character varying,
    shape_leng double precision,
    shape_area double precision,
    expediente character varying,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_7d469576_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_7d469576_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_7d469576_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_7d469576_id_seq OWNED BY catastro.stg_7d469576.id;


--
-- Name: stg_8e85e8bc; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_8e85e8bc (
    id integer NOT NULL,
    objectid integer,
    tipo_trami character varying,
    numero_tra character varying,
    institucio character varying,
    numero_pro character varying,
    fecha_adju date,
    nombre_pro character varying,
    numero_ide character varying,
    nacionalid character varying,
    estado_civ character varying,
    nombre_p_1 character varying,
    numero_i_1 character varying,
    nacional_1 character varying,
    estado_c_1 character varying,
    tipo_propi character varying,
    forma_adqu character varying,
    infraestru character varying,
    uso_suelo_ character varying,
    provincia character varying,
    canton character varying,
    parroquia character varying,
    sector character varying,
    clave_cata character varying,
    superficie double precision,
    centroide_ double precision,
    centroide1 double precision,
    analista_s character varying,
    observacio character varying,
    shape_leng double precision,
    shape_area double precision,
    expediente character varying,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_8e85e8bc_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_8e85e8bc_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_8e85e8bc_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_8e85e8bc_id_seq OWNED BY catastro.stg_8e85e8bc.id;


--
-- Name: stg_990df359; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_990df359 (
    id integer NOT NULL,
    objectid integer,
    tipo_trami character varying,
    numero_tra character varying,
    institucio character varying,
    numero_pro character varying,
    fecha_adju date,
    nombre_pro character varying,
    numero_ide character varying,
    nacionalid character varying,
    estado_civ character varying,
    nombre_p_1 character varying,
    numero_i_1 character varying,
    nacional_1 character varying,
    estado_c_1 character varying,
    tipo_propi character varying,
    forma_adqu character varying,
    infraestru character varying,
    uso_suelo_ character varying,
    provincia character varying,
    canton character varying,
    parroquia character varying,
    sector character varying,
    clave_cata character varying,
    superficie double precision,
    centroide_ double precision,
    centroide1 double precision,
    analista_s character varying,
    observacio character varying,
    shape_leng double precision,
    shape_area double precision,
    expediente character varying,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_990df359_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_990df359_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_990df359_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_990df359_id_seq OWNED BY catastro.stg_990df359.id;


--
-- Name: stg_be773d80; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_be773d80 (
    id integer NOT NULL,
    begin character varying,
    "end" character varying,
    nombres character varying,
    area double precision,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_be773d80_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_be773d80_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_be773d80_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_be773d80_id_seq OWNED BY catastro.stg_be773d80.id;


--
-- Name: stg_test_unif2; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.stg_test_unif2 (
    ogc_fid integer NOT NULL,
    altitude character varying,
    analista_s character varying,
    apellidos character varying,
    area character varying,
    area_ha double precision,
    area_m2 bigint,
    a_o integer,
    begin character varying,
    canton character varying,
    categories character varying,
    cde_ruc character varying,
    cdi_ruc character varying,
    cedula bigint,
    ced_ruc character varying,
    centroide double precision,
    centroide1 double precision,
    city character varying,
    cod_cat character varying,
    color integer,
    color_1 character varying,
    correo character varying,
    date_modif character varying,
    datos character varying,
    descrip character varying,
    descriptio character varying,
    displaymod character varying,
    dist double precision,
    elevation character varying,
    "end" character varying,
    entity character varying,
    estado_civ character varying,
    estado_c_1 character varying,
    este character varying,
    expediente character varying,
    fecha_adju date,
    fid bigint,
    forma_adqu character varying,
    ha bigint,
    id bigint,
    id_1 double precision,
    infraestru character varying,
    institucio character varying,
    layer character varying,
    linetype character varying,
    linewt integer,
    link character varying,
    lote bigint,
    manzana bigint,
    med double precision,
    medidas double precision,
    nacionalid character varying,
    nacional_1 character varying,
    name bigint,
    nombres character varying,
    nombre_pro character varying,
    nombre_p_1 character varying,
    nom_predio character varying,
    nom_previo character varying,
    norte character varying,
    numero_ide character varying,
    numero_i_1 character varying,
    numero_pro character varying,
    numero_tra character varying,
    num_lote integer,
    num_manz integer,
    num_maz integer,
    num_pred integer,
    num_predio integer,
    objectid integer,
    observ character varying,
    observacio character varying,
    oeste character varying,
    origen_shp character varying,
    parroquia character varying,
    path character varying,
    "position" character varying,
    predio bigint,
    propietrio character varying,
    provincia character varying,
    recinto character varying,
    rect character varying,
    refname character varying,
    sector character varying,
    shape_area double precision,
    shape_leng double precision,
    superficie double precision,
    sur character varying,
    symbol character varying,
    telef character varying,
    telefono bigint,
    telf character varying,
    tipo_propi character varying,
    tipo_trami character varying,
    type character varying,
    uso_suelo character varying,
    visible bigint,
    xcentroide double precision,
    ycentroide double precision,
    geom public.geometry(MultiPolygon,32717)
);


--
-- Name: stg_test_unif2_ogc_fid_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.stg_test_unif2_ogc_fid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stg_test_unif2_ogc_fid_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.stg_test_unif2_ogc_fid_seq OWNED BY catastro.stg_test_unif2.ogc_fid;


--
-- Name: tecnico; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.tecnico (
    id integer NOT NULL,
    nombre character varying(255) NOT NULL,
    cargo character varying(150),
    registro_senescyt character varying(100),
    empresa_id integer,
    activo boolean DEFAULT true,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: tecnico_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.tecnico_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tecnico_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.tecnico_id_seq OWNED BY catastro.tecnico.id;


--
-- Name: v_predio_completo; Type: VIEW; Schema: catastro; Owner: -
--

CREATE VIEW catastro.v_predio_completo AS
 SELECT p.id,
    p.cod_catastral,
    p.posesionario_id,
    p.empresa_id,
    p.proyecto_id,
    p.area_ha,
    p.geom,
    p.estado,
    p.fecha_creacion,
    p.fecha_baja,
    p.predio_padre_id,
    p.sector,
    p.parroquia,
    pos.cedula,
    pos.nombre AS nombre_posesionario,
    p.codigo_carta,
    p.nombre_carta,
    p.cuadricula_carta,
    p.codigo_anterior
   FROM (catastro.predio p
     LEFT JOIN catastro.posesionario pos ON ((p.posesionario_id = pos.id)));


--
-- Name: vertice; Type: TABLE; Schema: catastro; Owner: -
--

CREATE TABLE catastro.vertice (
    id integer NOT NULL,
    predio_id integer,
    codigo character varying(50) NOT NULL,
    geom public.geometry(Point,32717),
    coord_x numeric(14,4),
    coord_y numeric(14,4),
    cod_catastral character varying(100),
    estado character varying(20) DEFAULT 'Activo'::character varying,
    fecha_creacion date DEFAULT CURRENT_DATE,
    fecha_baja date,
    empresa_id integer
);


--
-- Name: vertice_id_seq; Type: SEQUENCE; Schema: catastro; Owner: -
--

CREATE SEQUENCE catastro.vertice_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vertice_id_seq; Type: SEQUENCE OWNED BY; Schema: catastro; Owner: -
--

ALTER SEQUENCE catastro.vertice_id_seq OWNED BY catastro.vertice.id;


--
-- Name: referencias_prediales; Type: TABLE; Schema: interoperabilidad; Owner: -
--

CREATE TABLE interoperabilidad.referencias_prediales (
    id integer NOT NULL,
    cod_catastral character varying(100),
    id_titular character varying(50),
    propietario character varying(255),
    nombre_predio character varying(255),
    sitio character varying(100),
    rcx numeric(14,4),
    rcy numeric(14,4),
    area_ref character varying(50),
    geom public.geometry(Point,32717),
    geom_4326 public.geometry(Point,4326),
    fecha_sincronizacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    activo boolean DEFAULT true
);


--
-- Name: referencias_prediales_id_seq; Type: SEQUENCE; Schema: interoperabilidad; Owner: -
--

CREATE SEQUENCE interoperabilidad.referencias_prediales_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: referencias_prediales_id_seq; Type: SEQUENCE OWNED BY; Schema: interoperabilidad; Owner: -
--

ALTER SEQUENCE interoperabilidad.referencias_prediales_id_seq OWNED BY interoperabilidad.referencias_prediales.id;


--
-- Name: configuracion_smtp; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.configuracion_smtp (
    id integer NOT NULL,
    smtp_server character varying(255) NOT NULL,
    smtp_port integer DEFAULT 587 NOT NULL,
    smtp_user character varying(255) NOT NULL,
    smtp_password character varying(255) NOT NULL,
    alert_email_to text NOT NULL,
    is_active boolean DEFAULT true,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: configuracion_smtp_id_seq; Type: SEQUENCE; Schema: seguridad; Owner: -
--

CREATE SEQUENCE seguridad.configuracion_smtp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: configuracion_smtp_id_seq; Type: SEQUENCE OWNED BY; Schema: seguridad; Owner: -
--

ALTER SEQUENCE seguridad.configuracion_smtp_id_seq OWNED BY seguridad.configuracion_smtp.id;


--
-- Name: logs; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.logs (
    id_log integer NOT NULL,
    tipo character varying(20) NOT NULL,
    accion character varying(100) NOT NULL,
    descripcion text NOT NULL,
    id_usuario integer,
    fecha timestamp without time zone,
    correo_enviado boolean
);


--
-- Name: logs_id_log_seq; Type: SEQUENCE; Schema: seguridad; Owner: -
--

CREATE SEQUENCE seguridad.logs_id_log_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: logs_id_log_seq; Type: SEQUENCE OWNED BY; Schema: seguridad; Owner: -
--

ALTER SEQUENCE seguridad.logs_id_log_seq OWNED BY seguridad.logs.id_log;


--
-- Name: operador_temporal; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.operador_temporal (
    id integer NOT NULL,
    nombre character varying(100) NOT NULL,
    apellido character varying(100) NOT NULL,
    nombre_completo character varying(200) GENERATED ALWAYS AS ((((nombre)::text || ' '::text) || (apellido)::text)) STORED,
    dispositivo_uuid character varying(100) NOT NULL,
    dispositivo_modelo character varying(150),
    ip_registro character varying(45),
    empresa_id integer,
    proyecto_id integer,
    activo boolean DEFAULT true,
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    ultimo_acceso timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: operador_temporal_id_seq; Type: SEQUENCE; Schema: seguridad; Owner: -
--

CREATE SEQUENCE seguridad.operador_temporal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: operador_temporal_id_seq; Type: SEQUENCE OWNED BY; Schema: seguridad; Owner: -
--

ALTER SEQUENCE seguridad.operador_temporal_id_seq OWNED BY seguridad.operador_temporal.id;


--
-- Name: roles; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.roles (
    id_rol integer NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion character varying,
    permisos jsonb DEFAULT '{}'::jsonb
);


--
-- Name: roles_id_rol_seq; Type: SEQUENCE; Schema: seguridad; Owner: -
--

CREATE SEQUENCE seguridad.roles_id_rol_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: roles_id_rol_seq; Type: SEQUENCE OWNED BY; Schema: seguridad; Owner: -
--

ALTER SEQUENCE seguridad.roles_id_rol_seq OWNED BY seguridad.roles.id_rol;


--
-- Name: usuario_proyecto; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.usuario_proyecto (
    usuario_id integer NOT NULL,
    proyecto_id integer NOT NULL
);


--
-- Name: usuarios; Type: TABLE; Schema: seguridad; Owner: -
--

CREATE TABLE seguridad.usuarios (
    id_usuario integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    id_rol integer,
    activo boolean,
    fecha_creacion timestamp without time zone,
    id_empresa integer,
    nombres character varying(100),
    apellidos character varying(100),
    cedula character varying(20),
    correo character varying(100)
);


--
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE; Schema: seguridad; Owner: -
--

CREATE SEQUENCE seguridad.usuarios_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: seguridad; Owner: -
--

ALTER SEQUENCE seguridad.usuarios_id_usuario_seq OWNED BY seguridad.usuarios.id_usuario;


--
-- Name: cantones id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cantones ALTER COLUMN id SET DEFAULT nextval('catastro.cantones_id_seq'::regclass);


--
-- Name: capa_dibujo id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capa_dibujo ALTER COLUMN id SET DEFAULT nextval('catastro.capa_dibujo_id_seq'::regclass);


--
-- Name: capas_adicionales id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capas_adicionales ALTER COLUMN id SET DEFAULT nextval('catastro.capas_adicionales_id_seq'::regclass);


--
-- Name: capas_cad_cartas id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capas_cad_cartas ALTER COLUMN id SET DEFAULT nextval('catastro.capas_cad_cartas_id_seq'::regclass);


--
-- Name: cartas_topograficas id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cartas_topograficas ALTER COLUMN id SET DEFAULT nextval('catastro.cartas_topograficas_id_seq'::regclass);


--
-- Name: ciudades id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ciudades ALTER COLUMN id SET DEFAULT nextval('catastro.ciudades_id_seq'::regclass);


--
-- Name: elementos_adicionales id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.elementos_adicionales ALTER COLUMN id SET DEFAULT nextval('catastro.elementos_adicionales_id_seq'::regclass);


--
-- Name: empresa id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa ALTER COLUMN id SET DEFAULT nextval('catastro.empresa_id_seq'::regclass);


--
-- Name: linea_lindero id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.linea_lindero ALTER COLUMN id SET DEFAULT nextval('catastro.linea_lindero_id_seq'::regclass);


--
-- Name: ortofotos_catalogo id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo ALTER COLUMN id SET DEFAULT nextval('catastro.ortofotos_catalogo_id_seq'::regclass);


--
-- Name: posesionario id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.posesionario ALTER COLUMN id SET DEFAULT nextval('catastro.posesionario_id_seq'::regclass);


--
-- Name: predio id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio ALTER COLUMN id SET DEFAULT nextval('catastro.predio_id_seq'::regclass);


--
-- Name: predio_historial id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio_historial ALTER COLUMN id SET DEFAULT nextval('catastro.predio_historial_id_seq'::regclass);


--
-- Name: provincias id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.provincias ALTER COLUMN id SET DEFAULT nextval('catastro.provincias_id_seq'::regclass);


--
-- Name: proyecto id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.proyecto ALTER COLUMN id SET DEFAULT nextval('catastro.proyecto_id_seq'::regclass);


--
-- Name: shape_00257a6d id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.shape_00257a6d ALTER COLUMN id SET DEFAULT nextval('catastro.shape_00257a6d_id_seq'::regclass);


--
-- Name: shape_e9f98d32 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.shape_e9f98d32 ALTER COLUMN id SET DEFAULT nextval('catastro.shape_e9f98d32_id_seq'::regclass);


--
-- Name: stg_0463eaf7 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_0463eaf7 ALTER COLUMN id SET DEFAULT nextval('catastro.stg_0463eaf7_id_seq'::regclass);


--
-- Name: stg_24174c69 ogc_fid; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_24174c69 ALTER COLUMN ogc_fid SET DEFAULT nextval('catastro.stg_24174c69_ogc_fid_seq'::regclass);


--
-- Name: stg_445a66d3 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_445a66d3 ALTER COLUMN id SET DEFAULT nextval('catastro.stg_445a66d3_id_seq'::regclass);


--
-- Name: stg_7d469576 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_7d469576 ALTER COLUMN id SET DEFAULT nextval('catastro.stg_7d469576_id_seq'::regclass);


--
-- Name: stg_8e85e8bc id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_8e85e8bc ALTER COLUMN id SET DEFAULT nextval('catastro.stg_8e85e8bc_id_seq'::regclass);


--
-- Name: stg_990df359 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_990df359 ALTER COLUMN id SET DEFAULT nextval('catastro.stg_990df359_id_seq'::regclass);


--
-- Name: stg_be773d80 id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_be773d80 ALTER COLUMN id SET DEFAULT nextval('catastro.stg_be773d80_id_seq'::regclass);


--
-- Name: stg_test_unif2 ogc_fid; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_test_unif2 ALTER COLUMN ogc_fid SET DEFAULT nextval('catastro.stg_test_unif2_ogc_fid_seq'::regclass);


--
-- Name: tecnico id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.tecnico ALTER COLUMN id SET DEFAULT nextval('catastro.tecnico_id_seq'::regclass);


--
-- Name: vertice id; Type: DEFAULT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.vertice ALTER COLUMN id SET DEFAULT nextval('catastro.vertice_id_seq'::regclass);


--
-- Name: referencias_prediales id; Type: DEFAULT; Schema: interoperabilidad; Owner: -
--

ALTER TABLE ONLY interoperabilidad.referencias_prediales ALTER COLUMN id SET DEFAULT nextval('interoperabilidad.referencias_prediales_id_seq'::regclass);


--
-- Name: configuracion_smtp id; Type: DEFAULT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.configuracion_smtp ALTER COLUMN id SET DEFAULT nextval('seguridad.configuracion_smtp_id_seq'::regclass);


--
-- Name: logs id_log; Type: DEFAULT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.logs ALTER COLUMN id_log SET DEFAULT nextval('seguridad.logs_id_log_seq'::regclass);


--
-- Name: operador_temporal id; Type: DEFAULT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.operador_temporal ALTER COLUMN id SET DEFAULT nextval('seguridad.operador_temporal_id_seq'::regclass);


--
-- Name: roles id_rol; Type: DEFAULT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.roles ALTER COLUMN id_rol SET DEFAULT nextval('seguridad.roles_id_rol_seq'::regclass);


--
-- Name: usuarios id_usuario; Type: DEFAULT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuarios ALTER COLUMN id_usuario SET DEFAULT nextval('seguridad.usuarios_id_usuario_seq'::regclass);


--
-- Name: cantones cantones_codigo_dpa_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cantones
    ADD CONSTRAINT cantones_codigo_dpa_key UNIQUE (codigo_dpa);


--
-- Name: cantones cantones_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cantones
    ADD CONSTRAINT cantones_pkey PRIMARY KEY (id);


--
-- Name: capa_dibujo capa_dibujo_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capa_dibujo
    ADD CONSTRAINT capa_dibujo_pkey PRIMARY KEY (id);


--
-- Name: capas_adicionales capas_adicionales_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capas_adicionales
    ADD CONSTRAINT capas_adicionales_pkey PRIMARY KEY (id);


--
-- Name: capas_cad_cartas capas_cad_cartas_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capas_cad_cartas
    ADD CONSTRAINT capas_cad_cartas_pkey PRIMARY KEY (id);


--
-- Name: cartas_topograficas cartas_topograficas_nombre_archivo_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cartas_topograficas
    ADD CONSTRAINT cartas_topograficas_nombre_archivo_key UNIQUE (nombre_archivo);


--
-- Name: cartas_topograficas cartas_topograficas_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cartas_topograficas
    ADD CONSTRAINT cartas_topograficas_pkey PRIMARY KEY (id);


--
-- Name: ciudades ciudades_codigo_dpa_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ciudades
    ADD CONSTRAINT ciudades_codigo_dpa_key UNIQUE (codigo_dpa);


--
-- Name: ciudades ciudades_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ciudades
    ADD CONSTRAINT ciudades_pkey PRIMARY KEY (id);


--
-- Name: codigo_catastral codigo_catastral_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.codigo_catastral
    ADD CONSTRAINT codigo_catastral_pkey PRIMARY KEY (codigo);


--
-- Name: elementos_adicionales elementos_adicionales_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.elementos_adicionales
    ADD CONSTRAINT elementos_adicionales_pkey PRIMARY KEY (id);


--
-- Name: empresa empresa_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa
    ADD CONSTRAINT empresa_pkey PRIMARY KEY (id);


--
-- Name: empresa_proyecto empresa_proyecto_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa_proyecto
    ADD CONSTRAINT empresa_proyecto_pkey PRIMARY KEY (empresa_id, proyecto_id);


--
-- Name: empresa empresa_ruc_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa
    ADD CONSTRAINT empresa_ruc_key UNIQUE (ruc);


--
-- Name: linea_lindero linea_lindero_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.linea_lindero
    ADD CONSTRAINT linea_lindero_pkey PRIMARY KEY (id);


--
-- Name: ortofotos_catalogo ortofotos_catalogo_nombre_archivo_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_nombre_archivo_key UNIQUE (nombre_archivo);


--
-- Name: ortofotos_catalogo ortofotos_catalogo_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_pkey PRIMARY KEY (id);


--
-- Name: posesionario posesionario_cedula_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.posesionario
    ADD CONSTRAINT posesionario_cedula_key UNIQUE (cedula);


--
-- Name: posesionario posesionario_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.posesionario
    ADD CONSTRAINT posesionario_pkey PRIMARY KEY (id);


--
-- Name: predio_historial predio_historial_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio_historial
    ADD CONSTRAINT predio_historial_pkey PRIMARY KEY (id);


--
-- Name: predio predio_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_pkey PRIMARY KEY (id);


--
-- Name: provincias provincias_codigo_dpa_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.provincias
    ADD CONSTRAINT provincias_codigo_dpa_key UNIQUE (codigo_dpa);


--
-- Name: provincias provincias_nombre_key; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.provincias
    ADD CONSTRAINT provincias_nombre_key UNIQUE (nombre);


--
-- Name: provincias provincias_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.provincias
    ADD CONSTRAINT provincias_pkey PRIMARY KEY (id);


--
-- Name: proyecto proyecto_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.proyecto
    ADD CONSTRAINT proyecto_pkey PRIMARY KEY (id);


--
-- Name: shape_00257a6d shape_00257a6d_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.shape_00257a6d
    ADD CONSTRAINT shape_00257a6d_pkey PRIMARY KEY (id);


--
-- Name: shape_e9f98d32 shape_e9f98d32_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.shape_e9f98d32
    ADD CONSTRAINT shape_e9f98d32_pkey PRIMARY KEY (id);


--
-- Name: stg_0463eaf7 stg_0463eaf7_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_0463eaf7
    ADD CONSTRAINT stg_0463eaf7_pkey PRIMARY KEY (id);


--
-- Name: stg_24174c69 stg_24174c69_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_24174c69
    ADD CONSTRAINT stg_24174c69_pkey PRIMARY KEY (ogc_fid);


--
-- Name: stg_445a66d3 stg_445a66d3_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_445a66d3
    ADD CONSTRAINT stg_445a66d3_pkey PRIMARY KEY (id);


--
-- Name: stg_7d469576 stg_7d469576_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_7d469576
    ADD CONSTRAINT stg_7d469576_pkey PRIMARY KEY (id);


--
-- Name: stg_8e85e8bc stg_8e85e8bc_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_8e85e8bc
    ADD CONSTRAINT stg_8e85e8bc_pkey PRIMARY KEY (id);


--
-- Name: stg_990df359 stg_990df359_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_990df359
    ADD CONSTRAINT stg_990df359_pkey PRIMARY KEY (id);


--
-- Name: stg_be773d80 stg_be773d80_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_be773d80
    ADD CONSTRAINT stg_be773d80_pkey PRIMARY KEY (id);


--
-- Name: stg_test_unif2 stg_test_unif2_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.stg_test_unif2
    ADD CONSTRAINT stg_test_unif2_pkey PRIMARY KEY (ogc_fid);


--
-- Name: tecnico tecnico_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.tecnico
    ADD CONSTRAINT tecnico_pkey PRIMARY KEY (id);


--
-- Name: vertice vertice_pkey; Type: CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.vertice
    ADD CONSTRAINT vertice_pkey PRIMARY KEY (id);


--
-- Name: referencias_prediales referencias_prediales_pkey; Type: CONSTRAINT; Schema: interoperabilidad; Owner: -
--

ALTER TABLE ONLY interoperabilidad.referencias_prediales
    ADD CONSTRAINT referencias_prediales_pkey PRIMARY KEY (id);


--
-- Name: referencias_prediales uq_ref_cod_rc; Type: CONSTRAINT; Schema: interoperabilidad; Owner: -
--

ALTER TABLE ONLY interoperabilidad.referencias_prediales
    ADD CONSTRAINT uq_ref_cod_rc UNIQUE (cod_catastral, rcx, rcy);


--
-- Name: configuracion_smtp configuracion_smtp_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.configuracion_smtp
    ADD CONSTRAINT configuracion_smtp_pkey PRIMARY KEY (id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (id_log);


--
-- Name: operador_temporal operador_temporal_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.operador_temporal
    ADD CONSTRAINT operador_temporal_pkey PRIMARY KEY (id);


--
-- Name: roles roles_nombre_key; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.roles
    ADD CONSTRAINT roles_nombre_key UNIQUE (nombre);


--
-- Name: roles roles_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.roles
    ADD CONSTRAINT roles_pkey PRIMARY KEY (id_rol);


--
-- Name: usuario_proyecto usuario_proyecto_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_pkey PRIMARY KEY (usuario_id, proyecto_id);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario);


--
-- Name: usuarios usuarios_username_key; Type: CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuarios
    ADD CONSTRAINT usuarios_username_key UNIQUE (username);


--
-- Name: idx_cad_archivo; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cad_archivo ON catastro.capas_cad_cartas USING btree (nombre_archivo);


--
-- Name: idx_cad_archivo_capa; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cad_archivo_capa ON catastro.capas_cad_cartas USING btree (nombre_archivo, capa_cad);


--
-- Name: idx_cad_capa; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cad_capa ON catastro.capas_cad_cartas USING btree (capa_cad);


--
-- Name: idx_cad_tipo_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cad_tipo_geom ON catastro.capas_cad_cartas USING btree (tipo_geometria);


--
-- Name: idx_capas_adicionales_tabla_db; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_capas_adicionales_tabla_db ON catastro.capas_adicionales USING btree (tabla_db);


--
-- Name: idx_cartas_topograficas_codigo; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cartas_topograficas_codigo ON catastro.cartas_topograficas USING btree (codigo);


--
-- Name: idx_cartas_topograficas_nombre_archivo; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_cartas_topograficas_nombre_archivo ON catastro.cartas_topograficas USING btree (nombre_archivo);


--
-- Name: idx_codigo_catastral_posesionario; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_codigo_catastral_posesionario ON catastro.codigo_catastral USING btree (posesionario_id);


--
-- Name: idx_elementos_adicionales_capa_id; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_elementos_adicionales_capa_id ON catastro.elementos_adicionales USING btree (capa_id);


--
-- Name: idx_elementos_adicionales_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_elementos_adicionales_geom ON catastro.elementos_adicionales USING gist (geom);


--
-- Name: idx_elementos_adicionales_propiedades_gin; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_elementos_adicionales_propiedades_gin ON catastro.elementos_adicionales USING gin (propiedades);


--
-- Name: idx_linea_lindero_cod_catastral; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_linea_lindero_cod_catastral ON catastro.linea_lindero USING btree (cod_catastral);


--
-- Name: idx_linea_lindero_empresa_id; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_linea_lindero_empresa_id ON catastro.linea_lindero USING btree (empresa_id);


--
-- Name: idx_linea_lindero_estado; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_linea_lindero_estado ON catastro.linea_lindero USING btree (estado);


--
-- Name: idx_linea_lindero_fecha_baja; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_linea_lindero_fecha_baja ON catastro.linea_lindero USING btree (fecha_baja);


--
-- Name: idx_linea_lindero_predio_id; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_linea_lindero_predio_id ON catastro.linea_lindero USING btree (predio_id);


--
-- Name: idx_ortofotos_catalogo_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_ortofotos_catalogo_geom ON catastro.ortofotos_catalogo USING gist (geom);


--
-- Name: idx_predio_empresa; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_empresa ON catastro.predio USING btree (empresa_id);


--
-- Name: idx_predio_estado; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_estado ON catastro.predio USING btree (estado);


--
-- Name: idx_predio_fecha_baja; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_fecha_baja ON catastro.predio USING btree (fecha_baja);


--
-- Name: idx_predio_fecha_creacion; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_fecha_creacion ON catastro.predio USING btree (fecha_creacion);


--
-- Name: idx_predio_posesionario; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_posesionario ON catastro.predio USING btree (posesionario_id);


--
-- Name: idx_predio_proyecto; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_predio_proyecto ON catastro.predio USING btree (proyecto_id);


--
-- Name: idx_vertice_cod_catastral; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_vertice_cod_catastral ON catastro.vertice USING btree (cod_catastral);


--
-- Name: idx_vertice_empresa_id; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_vertice_empresa_id ON catastro.vertice USING btree (empresa_id);


--
-- Name: idx_vertice_estado; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_vertice_estado ON catastro.vertice USING btree (estado);


--
-- Name: idx_vertice_fecha_baja; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_vertice_fecha_baja ON catastro.vertice USING btree (fecha_baja);


--
-- Name: idx_vertice_predio_id; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX idx_vertice_predio_id ON catastro.vertice USING btree (predio_id);


--
-- Name: predio_cod_catastral_active_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE UNIQUE INDEX predio_cod_catastral_active_idx ON catastro.predio USING btree (cod_catastral) WHERE (fecha_baja IS NULL);


--
-- Name: shape_00257a6d_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX shape_00257a6d_geom_geom_idx ON catastro.shape_00257a6d USING gist (geom);


--
-- Name: shape_e9f98d32_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX shape_e9f98d32_geom_geom_idx ON catastro.shape_e9f98d32 USING gist (geom);


--
-- Name: sidx_cad_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX sidx_cad_geom ON catastro.capas_cad_cartas USING gist (geom);


--
-- Name: sidx_linea_lindero_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX sidx_linea_lindero_geom ON catastro.linea_lindero USING gist (geom);


--
-- Name: sidx_predio_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX sidx_predio_geom ON catastro.predio USING gist (geom);


--
-- Name: sidx_vertice_geom; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX sidx_vertice_geom ON catastro.vertice USING gist (geom);


--
-- Name: stg_0463eaf7_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_0463eaf7_geom_geom_idx ON catastro.stg_0463eaf7 USING gist (geom);


--
-- Name: stg_24174c69_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_24174c69_geom_geom_idx ON catastro.stg_24174c69 USING gist (geom);


--
-- Name: stg_445a66d3_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_445a66d3_geom_geom_idx ON catastro.stg_445a66d3 USING gist (geom);


--
-- Name: stg_7d469576_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_7d469576_geom_geom_idx ON catastro.stg_7d469576 USING gist (geom);


--
-- Name: stg_8e85e8bc_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_8e85e8bc_geom_geom_idx ON catastro.stg_8e85e8bc USING gist (geom);


--
-- Name: stg_990df359_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_990df359_geom_geom_idx ON catastro.stg_990df359 USING gist (geom);


--
-- Name: stg_be773d80_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_be773d80_geom_geom_idx ON catastro.stg_be773d80 USING gist (geom);


--
-- Name: stg_test_unif2_geom_geom_idx; Type: INDEX; Schema: catastro; Owner: -
--

CREATE INDEX stg_test_unif2_geom_geom_idx ON catastro.stg_test_unif2 USING gist (geom);


--
-- Name: idx_ref_pred_cod; Type: INDEX; Schema: interoperabilidad; Owner: -
--

CREATE INDEX idx_ref_pred_cod ON interoperabilidad.referencias_prediales USING btree (cod_catastral);


--
-- Name: idx_ref_pred_geom; Type: INDEX; Schema: interoperabilidad; Owner: -
--

CREATE INDEX idx_ref_pred_geom ON interoperabilidad.referencias_prediales USING gist (geom);


--
-- Name: idx_ref_pred_geom4326; Type: INDEX; Schema: interoperabilidad; Owner: -
--

CREATE INDEX idx_ref_pred_geom4326 ON interoperabilidad.referencias_prediales USING gist (geom_4326);


--
-- Name: idx_ref_pred_titular; Type: INDEX; Schema: interoperabilidad; Owner: -
--

CREATE INDEX idx_ref_pred_titular ON interoperabilidad.referencias_prediales USING btree (id_titular);


--
-- Name: idx_operador_dispositivo; Type: INDEX; Schema: seguridad; Owner: -
--

CREATE INDEX idx_operador_dispositivo ON seguridad.operador_temporal USING btree (dispositivo_uuid);


--
-- Name: ix_seguridad_logs_id_log; Type: INDEX; Schema: seguridad; Owner: -
--

CREATE INDEX ix_seguridad_logs_id_log ON seguridad.logs USING btree (id_log);


--
-- Name: ix_seguridad_roles_id_rol; Type: INDEX; Schema: seguridad; Owner: -
--

CREATE INDEX ix_seguridad_roles_id_rol ON seguridad.roles USING btree (id_rol);


--
-- Name: ix_seguridad_usuarios_id_usuario; Type: INDEX; Schema: seguridad; Owner: -
--

CREATE INDEX ix_seguridad_usuarios_id_usuario ON seguridad.usuarios USING btree (id_usuario);


--
-- Name: cantones cantones_id_provincia_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.cantones
    ADD CONSTRAINT cantones_id_provincia_fkey FOREIGN KEY (id_provincia) REFERENCES catastro.provincias(id) ON DELETE CASCADE;


--
-- Name: capa_dibujo capa_dibujo_usuario_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capa_dibujo
    ADD CONSTRAINT capa_dibujo_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL;


--
-- Name: capas_adicionales capas_adicionales_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.capas_adicionales
    ADD CONSTRAINT capas_adicionales_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: ciudades ciudades_id_canton_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ciudades
    ADD CONSTRAINT ciudades_id_canton_fkey FOREIGN KEY (id_canton) REFERENCES catastro.cantones(id) ON DELETE CASCADE;


--
-- Name: codigo_catastral codigo_catastral_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.codigo_catastral
    ADD CONSTRAINT codigo_catastral_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: codigo_catastral codigo_catastral_posesionario_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.codigo_catastral
    ADD CONSTRAINT codigo_catastral_posesionario_id_fkey FOREIGN KEY (posesionario_id) REFERENCES catastro.posesionario(id) ON DELETE SET NULL;


--
-- Name: elementos_adicionales elementos_adicionales_capa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.elementos_adicionales
    ADD CONSTRAINT elementos_adicionales_capa_id_fkey FOREIGN KEY (capa_id) REFERENCES catastro.capas_adicionales(id) ON DELETE CASCADE;


--
-- Name: empresa_proyecto empresa_proyecto_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa_proyecto
    ADD CONSTRAINT empresa_proyecto_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: empresa empresa_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa
    ADD CONSTRAINT empresa_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id) ON DELETE SET NULL;


--
-- Name: empresa_proyecto empresa_proyecto_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.empresa_proyecto
    ADD CONSTRAINT empresa_proyecto_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id) ON DELETE CASCADE;


--
-- Name: linea_lindero linea_lindero_cod_catastral_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.linea_lindero
    ADD CONSTRAINT linea_lindero_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE;


--
-- Name: linea_lindero linea_lindero_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.linea_lindero
    ADD CONSTRAINT linea_lindero_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: linea_lindero linea_lindero_predio_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.linea_lindero
    ADD CONSTRAINT linea_lindero_predio_id_fkey FOREIGN KEY (predio_id) REFERENCES catastro.predio(id) ON DELETE CASCADE;


--
-- Name: ortofotos_catalogo ortofotos_catalogo_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: ortofotos_catalogo ortofotos_catalogo_id_canton_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_id_canton_fkey FOREIGN KEY (id_canton) REFERENCES catastro.cantones(id) ON DELETE SET NULL;


--
-- Name: ortofotos_catalogo ortofotos_catalogo_id_ciudad_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_id_ciudad_fkey FOREIGN KEY (id_ciudad) REFERENCES catastro.ciudades(id) ON DELETE SET NULL;


--
-- Name: ortofotos_catalogo ortofotos_catalogo_id_provincia_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_id_provincia_fkey FOREIGN KEY (id_provincia) REFERENCES catastro.provincias(id) ON DELETE SET NULL;


--
-- Name: ortofotos_catalogo ortofotos_catalogo_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.ortofotos_catalogo
    ADD CONSTRAINT ortofotos_catalogo_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id) ON DELETE SET NULL;


--
-- Name: posesionario posesionario_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.posesionario
    ADD CONSTRAINT posesionario_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: predio predio_cod_catastral_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE;


--
-- Name: predio predio_creado_por_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_creado_por_fkey FOREIGN KEY (creado_por) REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL;


--
-- Name: predio predio_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: predio_historial predio_historial_modificado_por_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio_historial
    ADD CONSTRAINT predio_historial_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL;


--
-- Name: predio_historial predio_historial_predio_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio_historial
    ADD CONSTRAINT predio_historial_predio_id_fkey FOREIGN KEY (predio_id) REFERENCES catastro.predio(id) ON DELETE CASCADE;


--
-- Name: predio predio_modificado_por_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_modificado_por_fkey FOREIGN KEY (modificado_por) REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL;


--
-- Name: predio predio_operador_temporal_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_operador_temporal_id_fkey FOREIGN KEY (operador_temporal_id) REFERENCES seguridad.operador_temporal(id);


--
-- Name: predio predio_posesionario_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_posesionario_id_fkey FOREIGN KEY (posesionario_id) REFERENCES catastro.posesionario(id) ON DELETE SET NULL;


--
-- Name: predio predio_predio_padre_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_predio_padre_id_fkey FOREIGN KEY (predio_padre_id) REFERENCES catastro.predio(id);


--
-- Name: predio predio_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.predio
    ADD CONSTRAINT predio_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id) ON DELETE SET NULL;


--
-- Name: proyecto proyecto_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.proyecto
    ADD CONSTRAINT proyecto_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: tecnico tecnico_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.tecnico
    ADD CONSTRAINT tecnico_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: vertice vertice_cod_catastral_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.vertice
    ADD CONSTRAINT vertice_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE;


--
-- Name: vertice vertice_empresa_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.vertice
    ADD CONSTRAINT vertice_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id) ON DELETE CASCADE;


--
-- Name: vertice vertice_predio_id_fkey; Type: FK CONSTRAINT; Schema: catastro; Owner: -
--

ALTER TABLE ONLY catastro.vertice
    ADD CONSTRAINT vertice_predio_id_fkey FOREIGN KEY (predio_id) REFERENCES catastro.predio(id) ON DELETE CASCADE;


--
-- Name: logs logs_id_usuario_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.logs
    ADD CONSTRAINT logs_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES seguridad.usuarios(id_usuario);


--
-- Name: operador_temporal operador_temporal_empresa_id_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.operador_temporal
    ADD CONSTRAINT operador_temporal_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES catastro.empresa(id);


--
-- Name: operador_temporal operador_temporal_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.operador_temporal
    ADD CONSTRAINT operador_temporal_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id);


--
-- Name: usuario_proyecto usuario_proyecto_proyecto_id_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_proyecto_id_fkey FOREIGN KEY (proyecto_id) REFERENCES catastro.proyecto(id) ON DELETE CASCADE;


--
-- Name: usuario_proyecto usuario_proyecto_usuario_id_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuario_proyecto
    ADD CONSTRAINT usuario_proyecto_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES seguridad.usuarios(id_usuario) ON DELETE CASCADE;


--
-- Name: usuarios usuarios_id_empresa_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuarios
    ADD CONSTRAINT usuarios_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES catastro.empresa(id) ON DELETE SET NULL;


--
-- Name: usuarios usuarios_id_rol_fkey; Type: FK CONSTRAINT; Schema: seguridad; Owner: -
--

ALTER TABLE ONLY seguridad.usuarios
    ADD CONSTRAINT usuarios_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES seguridad.roles(id_rol);


--
-- PostgreSQL database dump complete
--

\unrestrict ao4DFTUrEnMt6FLDjpeIeMmh3ZhVhShYGxGQZvPoRT9NLjEfsmxV1wd3Omw0DJ3

