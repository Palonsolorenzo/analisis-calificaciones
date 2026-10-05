import re
import pandas as pd
import numpy as np
from data_processor import STANDARD_COLUMNS

def analyze_subject(df: pd.DataFrame, subject_name: str, mapping: dict = None) -> dict:
    """
    Performs full statistical analysis for a single subject.
    Simplifies metrics by removing Q1/Q3 and Skewness.
    Uses standard clean column names for maximum Arrow and Streamlit compatibility.
    Filters out activities with 0 submissions so no empty rows appear.
    Adds automatic warning alert when Std Dev < 1.0 (Excessive Homogeneity).
    """
    cont_col = STANDARD_COLUMNS['CONTINUA']
    exam_col = STANDARD_COLUMNS['EXAM_FINAL']
    final_col = STANDARD_COLUMNS['NOTA_FINAL']
    
    def format_act_label(std_key: str, default_label: str) -> str:
        if mapping and mapping.get(std_key):
            raw = str(mapping[std_key])
            if len(raw) > 45:
                # If name is very long (e.g. Moodle full label), create clean readable summary
                match = re.search(r'ACT\.\d+\.CO', raw, re.IGNORECASE)
                if match:
                    act_code = match.group(0).upper()
                    rest = re.sub(r'^(?:Cuestionario|Tarea|Foro|Actividad):', '', raw, flags=re.IGNORECASE).strip()
                    rest = re.sub(r'\(Real\)$', '', rest).strip()
                    return rest if len(rest) <= 40 else f"{act_code}: {rest[:35]}..."
                return raw[:42] + '...'
            return raw
        return default_label

    act_cols = [
        (format_act_label('ACT_01', 'ACT.01.CO (Continua 1)'), STANDARD_COLUMNS['ACT_01']),
        (format_act_label('ACT_02', 'ACT.02.CO (Continua 2)'), STANDARD_COLUMNS['ACT_02']),
        (format_act_label('ACT_03', 'ACT.03.CO (Continua 3)'), STANDARD_COLUMNS['ACT_03']),
        (format_act_label('ACT_04', 'ACT.04.CO (Continua 4)'), STANDARD_COLUMNS['ACT_04']),
        (format_act_label('EXAM_P1', 'Examen Parte 1'), STANDARD_COLUMNS['EXAM_P1']),
        (format_act_label('EXAM_P2', 'Examen Parte 2'), STANDARD_COLUMNS['EXAM_P2'])
    ]

    total_enrolled = len(df)
    
    # Evaluated students: those with at least one grade > 0.0 in continuous, exam, or final
    eval_condition = (df.get(final_col, pd.Series(dtype=float)) > 0.0) | \
                     (df.get(cont_col, pd.Series(dtype=float)) > 0.0) | \
                     (df.get(exam_col, pd.Series(dtype=float)) > 0.0)
    evaluated_df = df[eval_condition].copy() if len(df) > 0 else df
    num_evaluated = len(evaluated_df)
    num_np = total_enrolled - num_evaluated

    # Final grade metrics among submitted/evaluated (> 0.0)
    valid_final = df[df[final_col] > 0.0][final_col].dropna() if final_col in df.columns else pd.Series(dtype=float)
    num_passed = int((valid_final >= 5.0).sum())
    num_failed = int((valid_final < 5.0).sum())

    pct_passed_eval = round(float(num_passed / len(valid_final) * 100), 1) if len(valid_final) > 0 else 0.0
    pct_failed_eval = round(float(num_failed / len(valid_final) * 100), 1) if len(valid_final) > 0 else 0.0
    pct_passed_total = round(float(num_passed / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0
    pct_np_total = round(float(num_np / total_enrolled * 100), 1) if total_enrolled > 0 else 0.0

    # Descriptive Stats Helper (Filters out 0.0 and NaNs, simplified metrics)
    def get_stats(series: pd.Series):
        if series is None or series.empty:
            return {'count': 0, 'pct_part': 0.0, 'mean': 0.0, 'std': 0.0, 'median': 0.0, 'min': 0.0, 'max': 0.0, 'floor': 0.0, 'ceiling': 0.0}
        
        s = series.dropna()
        s = pd.to_numeric(s, errors='coerce').dropna()
        s = s[s > 0.0]
        
        if len(s) == 0:
            return {
                'count': 0,
                'pct_part': 0.0,
                'mean': 0.0,
                'std': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'floor': 0.0,
                'ceiling': 0.0
            }
        
        pct_part = (len(s) / num_evaluated * 100) if num_evaluated > 0 else 0.0
        floor_pct = ((s < 5.0).sum() / len(s) * 100) if len(s) > 0 else 0.0
        ceiling_pct = ((s >= 9.0).sum() / len(s) * 100) if len(s) > 0 else 0.0

        mean_val = float(s.mean())
        std_val = float(s.std()) if len(s) > 1 else 0.0
        median_val = float(s.median())
        min_val = float(s.min())
        max_val = float(s.max())

        return {
            'count': int(len(s)),
            'pct_part': round(pct_part, 1),
            'mean': round(mean_val, 2) if not np.isnan(mean_val) else 0.0,
            'std': round(std_val, 2) if not np.isnan(std_val) else 0.0,
            'median': round(median_val, 2) if not np.isnan(median_val) else 0.0,
            'min': round(min_val, 2) if not np.isnan(min_val) else 0.0,
            'max': round(max_val, 2) if not np.isnan(max_val) else 0.0,
            'floor': round(floor_pct, 1),
            'ceiling': round(ceiling_pct, 1)
        }

    stats_final = get_stats(df.get(final_col, pd.Series(dtype=float)))
    stats_cont = get_stats(df.get(cont_col, pd.Series(dtype=float)))
    stats_exam = get_stats(df.get(exam_col, pd.Series(dtype=float)))

    pct_floor = stats_final['floor']
    pct_ceiling = stats_final['ceiling']

    # Detailed Per-Activity Statistics Engine
    activity_stats_list = []
    
    all_target_cols = act_cols + [
        ('Resultado Ev. Continua', cont_col),
        ('Resultado Examen Final', exam_col),
        ('Nota Final Asignatura', final_col)
    ]

    for label, col_name in all_target_cols:
        if col_name not in df.columns:
            continue

        st_dict = get_stats(df[col_name])
        
        # Skip optional continuous tasks or exam parts if they have 0 submitted entries
        if st_dict['count'] == 0 and col_name not in [cont_col, exam_col, final_col]:
            continue

        if col_name != final_col:
            valid_pairs = df[[col_name, final_col]].dropna()
            valid_pairs = valid_pairs[(pd.to_numeric(valid_pairs[col_name], errors='coerce') > 0.0) & (pd.to_numeric(valid_pairs[final_col], errors='coerce') > 0.0)]
            if len(valid_pairs) > 2:
                r_val = float(valid_pairs.corr().iloc[0, 1])
                r_final = round(r_val, 2) if not np.isnan(r_val) else 0.0
            else:
                r_final = 0.0
        else:
            r_final = 1.0

        mean_val = st_dict['mean']
        diff_label = 'Alta (<5.0)' if mean_val < 5.0 else ('Media (5.0-7.0)' if mean_val <= 7.0 else 'Baja (>7.0)')

        activity_stats_list.append({
            'Actividad / Prueba': str(label),
            'Entregados': int(st_dict['count']),
            'Participacion (%)': float(st_dict['pct_part']),
            'Media': float(st_dict['mean']),
            'Mediana': float(st_dict['median']),
            'Desviacion Tipica': float(st_dict['std']),
            'Minimo': float(st_dict['min']),
            'Maximo': float(st_dict['max']),
            'Efecto Suelo (<5)': float(st_dict['floor']),
            'Efecto Techo (>=9)': float(st_dict['ceiling']),
            'r c/ Nota Final': float(r_final),
            'Dificultad': str(diff_label)
        })

    activity_stats_df = pd.DataFrame(activity_stats_list)

    # Correlations
    positive_df = df[(pd.to_numeric(df[cont_col], errors='coerce') > 0.0) & (pd.to_numeric(df[exam_col], errors='coerce') > 0.0) & (pd.to_numeric(df[final_col], errors='coerce') > 0.0)]
    if len(positive_df) > 2:
        corr_matrix = positive_df[[cont_col, exam_col, final_col]].corr().round(3)
        r_cont_exam = float(corr_matrix.loc[cont_col, exam_col]) if not np.isnan(corr_matrix.loc[cont_col, exam_col]) else 0.0
        r_cont_final = float(corr_matrix.loc[cont_col, final_col]) if not np.isnan(corr_matrix.loc[cont_col, final_col]) else 0.0
        r_exam_final = float(corr_matrix.loc[exam_col, final_col]) if not np.isnan(corr_matrix.loc[exam_col, final_col]) else 0.0
    else:
        corr_matrix = pd.DataFrame()
        r_cont_exam = 0.0
        r_cont_final = 0.0
        r_exam_final = 0.0

    # Automated Correlation & Homogeneity Alerts
    alerts = []

    # ALERT 1: Excessive Homogeneity Alert (Std Dev < 1.0)
    if stats_final['std'] > 0.0 and stats_final['std'] < 1.0 and stats_final['count'] > 3:
        alerts.append({
            'type': 'WARNING',
            'title': 'Excesiva Homogeneidad en Calificaciones',
            'message': f'La Desviación Típica de la asignatura es inusualmente baja (σ = {stats_final["std"]:.2f} < 1.0). Las notas están excesivamente agrupadas alrededor de la media, lo que puede indicar falta de capacidad discriminatoria en las pruebas o evaluaciones demasiado uniformes.'
        })

    # ALERT 2: Pearson Correlation Alerts
    if r_cont_exam < 0:
        alerts.append({
            'type': 'CRITICAL',
            'title': 'Correlación Inversa Continua vs Examen',
            'message': f'La correlación entre la Evaluación Continua y el Examen es negativa (r = {r_cont_exam:.2f}). Indicio severo de que la evaluación continua no prepara al alumno para el examen o existe desalineación metodológica.'
        })
    elif r_cont_exam < 0.3:
        alerts.append({
            'type': 'WARNING',
            'title': 'Correlación Débil Continua vs Examen',
            'message': f'La correlación entre la Evaluación Continua y el Examen es débil (r = {r_cont_exam:.2f}). Se recomienda revisar la coherencia pedagógica entre actividades intermedias y la prueba final.'
        })
    elif r_cont_exam >= 0.7:
        alerts.append({
            'type': 'SUCCESS',
            'title': 'Excelente Alineación de Evaluación',
            'message': f'Alta correlación entre Evaluación Continua y Examen (r = {r_cont_exam:.2f}). Las actividades diagnósticas reflejan adecuadamente el desempeño final.'
        })

    # Discrepancy & Outlier Identification
    discrepancies = []

    for idx, row in df.iterrows():
        s_id = str(row.get('STUDENT_ID', row.get('[[id]]', f'Estudiante_{idx+1}')))
        c_val = pd.to_numeric(row.get(cont_col), errors='coerce')
        e_val = pd.to_numeric(row.get(exam_col), errors='coerce')
        f_val = pd.to_numeric(row.get(final_col), errors='coerce')

        if pd.notnull(c_val) and pd.notnull(e_val) and c_val > 0.0 and e_val > 0.0:
            diff = c_val - e_val
            # Continuous Inflation
            if c_val >= 7.0 and e_val < 4.0:
                discrepancies.append({
                    'STUDENT_ID': s_id,
                    'type': 'Inflación Continua / Caída Examen',
                    'severity': 'Alta',
                    'continua': float(c_val),
                    'examen': float(e_val),
                    'nota_final': float(f_val) if pd.notnull(f_val) else round(c_val*0.4 + e_val*0.6, 2),
                    'diferencia': round(float(diff), 2),
                    'diagnostico': 'Nota continua muy elevada pero suspenso grave en examen. Posible copia en entregas o falta de preparación individual.'
                })
            # Exam Recovery
            elif c_val < 4.0 and e_val >= 7.0:
                discrepancies.append({
                    'STUDENT_ID': s_id,
                    'type': 'Recuperación Excepcional en Examen',
                    'severity': 'Media',
                    'continua': float(c_val),
                    'examen': float(e_val),
                    'nota_final': float(f_val) if pd.notnull(f_val) else round(c_val*0.4 + e_val*0.6, 2),
                    'diferencia': round(float(diff), 2),
                    'diagnostico': 'Baja participación o entregas en continua, pero dominio excelente en examen final.'
                })

    discrepancies_df = pd.DataFrame(discrepancies) if len(discrepancies) > 0 else pd.DataFrame(columns=['STUDENT_ID', 'type', 'severity', 'continua', 'examen', 'nota_final', 'diferencia', 'diagnostico'])

    # Risk level determination
    if r_cont_exam < 0 or (len(discrepancies_df) > 0 and len(discrepancies_df[discrepancies_df['severity'] == 'Alta']) >= 3) or pct_failed_eval > 50:
        risk_level = 'Crítico'
    elif r_cont_exam < 0.3 or len(discrepancies_df) >= 2 or pct_failed_eval > 35 or (stats_final['std'] > 0 and stats_final['std'] < 1.0):
        risk_level = 'Medio'
    else:
        risk_level = 'Bajo'

    return {
        'subject_name': subject_name,
        'total_enrolled': total_enrolled,
        'num_evaluated': num_evaluated,
        'num_passed': num_passed,
        'num_failed': num_failed,
        'num_np': num_np,
        'pct_passed_eval': round(pct_passed_eval, 1),
        'pct_failed_eval': round(pct_failed_eval, 1),
        'pct_passed_total': round(pct_passed_total, 1),
        'pct_np_total': round(pct_np_total, 1),
        'stats_final': stats_final,
        'stats_cont': stats_cont,
        'stats_exam': stats_exam,
        'activity_stats_df': activity_stats_df,
        'pct_floor': round(pct_floor, 1),
        'pct_ceiling': round(pct_ceiling, 1),
        'corr_matrix': corr_matrix,
        'r_cont_exam': round(float(r_cont_exam), 3),
        'r_cont_final': round(float(r_cont_final), 3),
        'r_exam_final': round(float(r_exam_final), 3),
        'alerts': alerts,
        'discrepancies_df': discrepancies_df,
        'task_metrics_df': activity_stats_df,
        'risk_level': risk_level
    }

def consolidate_degree_analysis(subjects_data: list) -> dict:
    """
    Consolidates data across all subjects in the degree/titulación.
    """
    if not subjects_data:
        return {
            'summary_df': pd.DataFrame(),
            'tot_subjects': 0,
            'tot_students': 0,
            'tot_evaluated': 0,
            'avg_pass_rate': 0.0,
            'avg_final_grade': 0.0,
            'avg_r_cont_exam': 0.0,
            'anomalies_df': pd.DataFrame()
        }

    summary_rows = []
    for s in subjects_data:
        summary_rows.append({
            'Asignatura': str(s.get('subject_name', '')),
            'Matriculados': int(s.get('total_enrolled', 0)),
            'Evaluados': int(s.get('num_evaluated', 0)),
            '% Aprobados (eval)': float(s.get('pct_passed_eval', 0.0)),
            'Media Final (presentados)': float(s.get('stats_final', {}).get('mean', 0.0)),
            'Desv. Tip. Final': float(s.get('stats_final', {}).get('std', 0.0)),
            'Media Continua': float(s.get('stats_cont', {}).get('mean', 0.0)),
            'Media Examen': float(s.get('stats_exam', {}).get('mean', 0.0)),
            'Diferencia (Cont-Exam)': round(float(s.get('stats_cont', {}).get('mean', 0.0) - s.get('stats_exam', {}).get('mean', 0.0)), 2),
            'r(Cont, Exam)': float(s.get('r_cont_exam', 0.0)),
            'Casos Discrepantes': int(len(s.get('discrepancies_df', []))),
            'Nivel Riesgo': str(s.get('risk_level', 'Bajo'))
        })

    summary_df = pd.DataFrame(summary_rows)

    tot_students = int(summary_df['Matriculados'].sum()) if not summary_df.empty else 0
    tot_evaluated = int(summary_df['Evaluados'].sum()) if not summary_df.empty else 0
    avg_pass_rate = round(float(summary_df['% Aprobados (eval)'].mean()), 1) if not summary_df.empty else 0.0
    avg_final_grade = round(float(summary_df['Media Final (presentados)'].mean()), 2) if not summary_df.empty else 0.0
    avg_r_cont_exam = round(float(summary_df['r(Cont, Exam)'].mean()), 2) if not summary_df.empty else 0.0
    std_pass_rate = float(summary_df['% Aprobados (eval)'].std()) if len(summary_df) > 1 else 0.0

    anomalies = []

    for idx, row in summary_df.iterrows():
        subj = row['Asignatura']

        if row['% Aprobados (eval)'] < (avg_pass_rate - 1.5 * std_pass_rate) and row['% Aprobados (eval)'] < 40:
            anomalies.append({
                'Asignatura': subj,
                'Tipo Anomalía': 'Tasa de Suspensos Desproporcionada',
                'Detalle': f'Aprobados ({row["% Aprobados (eval)"]}%) muy por debajo del promedio de la titulación ({avg_pass_rate}%).'
            })

        if row['r(Cont, Exam)'] < 0.2:
            anomalies.append({
                'Asignatura': subj,
                'Tipo Anomalía': 'Desalineación Evaluación Continua/Examen',
                'Detalle': f'Correlación r = {row["r(Cont, Exam)"]} anormalmente baja comparada con el resto del plan de estudios.'
            })

        if row['Diferencia (Cont-Exam)'] > 3.0:
            anomalies.append({
                'Asignatura': subj,
                'Tipo Anomalía': 'Sesgo de Inflación en Continua',
                'Detalle': f'La media de continua ({row["Media Continua"]}) supera a la del examen ({row["Media Examen"]}) por {row["Diferencia (Cont-Exam)"]} puntos.'
            })

        if row['Desv. Tip. Final'] > 0 and row['Desv. Tip. Final'] < 1.0:
            anomalies.append({
                'Asignatura': subj,
                'Tipo Anomalía': 'Excesiva Homogeneidad (σ < 1.0)',
                'Detalle': f'Desviación típica inusualmente baja (σ = {row["Desv. Tip. Final"]:.2f}). Posible falta de capacidad discriminatoria en los exámenes o evaluaciones uniformes.'
            })

    anomalies_df = pd.DataFrame(anomalies) if len(anomalies) > 0 else pd.DataFrame(columns=['Asignatura', 'Tipo Anomalía', 'Detalle'])

    return {
        'summary_df': summary_df,
        'tot_subjects': len(subjects_data),
        'tot_students': tot_students,
        'tot_evaluated': tot_evaluated,
        'avg_pass_rate': avg_pass_rate,
        'avg_final_grade': avg_final_grade,
        'avg_r_cont_exam': avg_r_cont_exam,
        'anomalies_df': anomalies_df
    }
