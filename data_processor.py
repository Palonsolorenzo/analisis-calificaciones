import re
import os
import pandas as pd
import numpy as np

# Standard column keys used internally across the app
STANDARD_COLUMNS = {
    'ACT_01': 'ACT.01.CO',
    'ACT_02': 'ACT.02.CO',
    'ACT_03': 'ACT.03.CO',
    'ACT_04': 'ACT.04.CO',
    'EXAM_P1': 'Total Prueba final parte 1',
    'EXAM_P2': 'Total Prueba final parte 2',
    'CONTINUA': 'Resultado de evaluación continua',
    'EXAM_FINAL': 'Resultado pruebas de evaluación final',
    'NOTA_FINAL': 'Nota final convocatoria ordinaria'
}

def clean_subject_name(filename_or_title: str) -> str:
    """Extract clean subject name from filename or title."""
    base = os.path.basename(filename_or_title)
    name = os.path.splitext(base)[0]
    # Remove bracketed codes like (NUT2-2526-2) or [CODE]
    name = re.sub(r'^\s*[\(\[\{].*?[\)\]\}]\s*', '', name)
    name = re.sub(r'\s*Calificaciones\s*', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*Notas\s*', '', name, flags=re.IGNORECASE)
    name = name.strip(' -_')
    return name if name else base

def auto_map_columns(df_columns: list) -> dict:
    """
    Automatically maps raw DataFrame column names to standard keys.
    Returns a dict: {standard_key: matched_raw_column_name or None}
    Uses multi-stage priority matching to eliminate cross-matching and collisions.
    """
    mapping = {k: None for k in STANDARD_COLUMNS.keys()}
    mapping['STUDENT_ID'] = None

    cols = [str(c).strip() for c in df_columns]
    used_cols = set()

    # --- STAGE 1: Student ID / Name ---
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ['student_id', '[[id]]', 'expediente', 'matricula', 'matrícula', 'id alumno', 'id estudiante']):
            mapping['STUDENT_ID'] = c
            used_cols.add(c)
            break
    if not mapping['STUDENT_ID']:
        for c in cols:
            cl = c.lower()
            if any(k in cl for k in ['alumno', 'estudiante', 'nombre', 'apellidos', 'id']):
                mapping['STUDENT_ID'] = c
                used_cols.add(c)
                break

    # --- STAGE 2: Summary / Aggregate Columns ---
    # Nota Final
    for c in cols:
        if c in used_cols: continue
        cl = c.lower()
        if any(k in cl for k in ['nota final', 'convocatoria ordinaria', 'calificación final', 'calificacion final', 'nota global', 'nota definitiva']):
            mapping['NOTA_FINAL'] = c
            used_cols.add(c)
            break
    
    # Continua Aggregate
    for c in cols:
        if c in used_cols: continue
        cl = c.lower()
        if 'evaluaci' in cl and 'continua' in cl and not any(k in cl for k in ['act', 'pec', 'tarea', 'cuestionario']):
            mapping['CONTINUA'] = c
            used_cols.add(c)
            break
        elif 'continua' in cl and not any(k in cl for k in ['act', 'pec', 'tarea', 'cuestionario']):
            mapping['CONTINUA'] = c
            used_cols.add(c)
            break
            
    # Exam Final Aggregate
    for c in cols:
        if c in used_cols: continue
        cl = c.lower()
        if ('evaluaci' in cl or 'prueba' in cl) and 'final' in cl and not any(k in cl for k in ['parte', 'p1', 'p2']):
            mapping['EXAM_FINAL'] = c
            used_cols.add(c)
            break
        elif 'examen' in cl and not any(k in cl for k in ['parte', 'p1', 'p2', 'parcial']):
            mapping['EXAM_FINAL'] = c
            used_cols.add(c)
            break

    # --- STAGE 3: Exam Parts (EXAM_P1, EXAM_P2) ---
    for c in cols:
        if c in used_cols: continue
        cl = c.lower()
        if re.search(r'parte\s*0?1\b|p1\b|prueba final parte 1|examen parte 1', cl):
            mapping['EXAM_P1'] = c
            used_cols.add(c)
            break

    for c in cols:
        if c in used_cols: continue
        cl = c.lower()
        if re.search(r'parte\s*0?2\b|p2\b|prueba final parte 2|examen parte 2', cl):
            mapping['EXAM_P2'] = c
            used_cols.add(c)
            break

    # --- STAGE 4: Continuous Activities (ACT_01 to ACT_04) ---
    act_keys = [('ACT_01', '1'), ('ACT_02', '2'), ('ACT_03', '3'), ('ACT_04', '4')]

    # Priority 4A: Explicit ACT.0X / ACT_0X / ACT 0X codes (Moodle exports like ACT.01.CO)
    for key, num in act_keys:
        if mapping[key]: continue
        pattern = re.compile(rf'act[\.\_\-\s]*0?{num}\b', re.IGNORECASE)
        for c in cols:
            if c in used_cols: continue
            if pattern.search(c):
                mapping[key] = c
                used_cols.add(c)
                break

    # Priority 4B: Named activity keywords (Actividad 1, PEC 1, Tarea 1, Cuestionario 1, Trabajo 1, Unidad 1, Tema 1, Foro 1)
    keywords = ['actividad', 'act', 'pec', 'tarea', 'cuestionario', 'trabajo', 'entregable', 'unidad', 'tema', 'foro', 'ud', 'practica', 'práctica']
    kw_pattern = '|'.join(keywords)
    
    for key, num in act_keys:
        if mapping[key]: continue
        pattern = re.compile(rf'(?:{kw_pattern})[\.\_\-\s]*0?{num}\b', re.IGNORECASE)
        for c in cols:
            if c in used_cols: continue
            if pattern.search(c):
                mapping[key] = c
                used_cols.add(c)
                break

    # Priority 4C: Search for digit 1, 2, 3, 4 if column is numeric evaluation column
    for key, num in act_keys:
        if mapping[key]: continue
        pattern = re.compile(rf'\b0?{num}\b')
        for c in cols:
            if c in used_cols: continue
            cl = c.lower()
            if pattern.search(cl) and not any(k in cl for k in ['id', 'expediente', 'total', 'final', 'resumen', 'promedio']):
                mapping[key] = c
                used_cols.add(c)
                break

    # Priority 4D: Dynamic Fallback - Any unused non-ID column
    for key, num in act_keys:
        if mapping[key]: continue
        for c in cols:
            if c in used_cols: continue
            cl = c.lower()
            if not any(k in cl for k in ['id', 'nombre', 'alumno', 'expediente', 'total', 'final', 'resumen', 'promedio']):
                mapping[key] = c
                used_cols.add(c)
                break

    return mapping

def clean_dataframe_from_mapping(df: pd.DataFrame, mapping: dict, subject_name: str = "Asignatura") -> pd.DataFrame:
    """
    Cleans DataFrame given a specific column mapping dict.
    Returns cleaned_df with standard columns.
    """
    df_copy = df.copy()
    df_copy.columns = [str(c).strip() for c in df_copy.columns]

    cleaned_df = pd.DataFrame()

    # Student ID
    student_col = mapping.get('STUDENT_ID')
    if student_col and student_col in df_copy.columns:
        cleaned_df['STUDENT_ID'] = df_copy[student_col].astype(str)
    else:
        cleaned_df['STUDENT_ID'] = [f"Estudiante_{i+1}" for i in range(len(df_copy))]

    # Numeric conversion for grade columns
    num_keys = ['ACT_01', 'ACT_02', 'ACT_03', 'ACT_04', 'EXAM_P1', 'EXAM_P2', 'CONTINUA', 'EXAM_FINAL', 'NOTA_FINAL']
    
    for key in num_keys:
        raw_col = mapping.get(key)
        if raw_col and raw_col in df_copy.columns:
            s = df_copy[raw_col].astype(str).str.replace(',', '.').str.strip()
            s = s.replace(['-', 'NP', 'n/a', 'N/A', 'nan', 'NaN', 'None', ''], np.nan)
            cleaned_df[STANDARD_COLUMNS[key]] = pd.to_numeric(s, errors='coerce')
        else:
            cleaned_df[STANDARD_COLUMNS[key]] = np.nan

    # Recalculate or fill aggregate columns if missing but components exist
    c_cols = [STANDARD_COLUMNS['ACT_01'], STANDARD_COLUMNS['ACT_02'], STANDARD_COLUMNS['ACT_03'], STANDARD_COLUMNS['ACT_04']]
    cont_col = STANDARD_COLUMNS['CONTINUA']
    if cleaned_df[cont_col].isnull().all() and cleaned_df[c_cols].notnull().any().any():
        cleaned_df[cont_col] = cleaned_df[c_cols].mean(axis=1, skipna=True)

    e_cols = [STANDARD_COLUMNS['EXAM_P1'], STANDARD_COLUMNS['EXAM_P2']]
    exam_col = STANDARD_COLUMNS['EXAM_FINAL']
    if cleaned_df[exam_col].isnull().all() and cleaned_df[e_cols].notnull().any().any():
        cleaned_df[exam_col] = cleaned_df[e_cols].mean(axis=1, skipna=True)

    final_col = STANDARD_COLUMNS['NOTA_FINAL']
    if cleaned_df[final_col].isnull().all():
        c_series = cleaned_df[cont_col].fillna(0.0)
        e_series = cleaned_df[exam_col].fillna(0.0)
        cleaned_df[final_col] = c_series * 0.4 + e_series * 0.6
        cleaned_df.loc[cleaned_df[cont_col].isnull() & cleaned_df[exam_col].isnull(), final_col] = np.nan

    # Round all grades to 2 decimal places
    grade_cols = [STANDARD_COLUMNS[k] for k in num_keys]
    cleaned_df[grade_cols] = cleaned_df[grade_cols].round(2)

    return cleaned_df

def load_and_clean_file(file_or_path, filename: str = None) -> tuple:
    """
    Reads an uploaded Excel (.xlsx, .xls), CSV, or ODS file, maps columns,
    cleans numeric values, and returns (df_cleaned, column_mapping, subject_name, raw_df).
    """
    if filename is None and hasattr(file_or_path, 'name'):
        filename = file_or_path.name
    elif filename is None and isinstance(file_or_path, str):
        filename = file_or_path

    subject_name = clean_subject_name(filename)
    ext = os.path.splitext(filename)[1].lower() if filename else ''

    if ext == '.csv':
        try:
            df = pd.read_csv(file_or_path, sep=None, engine='python')
        except Exception:
            df = pd.read_csv(file_or_path, sep=';')
    elif ext in ['.ods']:
        df = pd.read_excel(file_or_path, engine='odf')
    else:
        df = pd.read_excel(file_or_path)

    df.columns = [str(c).strip() for c in df.columns]
    mapping = auto_map_columns(df.columns)
    cleaned_df = clean_dataframe_from_mapping(df, mapping, subject_name)

    return cleaned_df, mapping, subject_name, df
