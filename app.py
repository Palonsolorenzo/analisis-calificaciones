import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as bg
import plotly.subplots as sp
import io
import os
import re

from data_processor import load_and_clean_file, clean_dataframe_from_mapping, auto_map_columns, STANDARD_COLUMNS
from analytics import analyze_subject, consolidate_degree_analysis
from sample_data_generator import generate_sample_degree
from report_generator import (
    generate_subject_markdown, generate_degree_markdown,
    generate_subject_pdf, generate_degree_pdf
)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Analítica Académica & Auditoría de Titulación",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E3A8A;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
    }
    .filter-badge {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-size: 0.9rem;
        color: #1E40AF;
    }
    .alert-critical {
        background-color: #FEF2F2;
        border-left: 4px solid #EF4444;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .alert-warning {
        background-color: #FFFBEB;
        border-left: 4px solid #F59E0B;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
    .alert-success {
        background-color: #F0FDF4;
        border-left: 4px solid #10B981;
        padding: 12px;
        border-radius: 4px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State safely
if 'subjects_data' not in st.session_state:
    st.session_state['subjects_data'] = []
if 'raw_dfs' not in st.session_state:
    st.session_state['raw_dfs'] = {}
if 'mappings' not in st.session_state:
    st.session_state['mappings'] = {}
if 'clean_dfs' not in st.session_state:
    st.session_state['clean_dfs'] = {}

# Sidebar Title & Uploads
with st.sidebar:
    st.image("https://img.icons8.com/color/96/education.png", width=64)
    st.title("🎓 Analítica Académica")
    st.markdown("**Auditoría de Calidad y Rendimiento de Titulación**")
    st.markdown("---")

    st.subheader("📁 Carga Masiva de Asignaturas")
    uploaded_files = st.file_uploader(
        "Selecciona archivos Excel (.xlsx), CSV (.csv) u ODS (.ods):",
        type=['xlsx', 'xls', 'csv', 'ods'],
        accept_multiple_files=True
    )

    st.markdown("---")
    st.markdown("**¿Quieres probar la aplicación de inmediato?**")
    if st.button("⚡ Cargar Datos de Ejemplo (5 Asignaturas)", use_container_width=True):
        sample_dict = generate_sample_degree()
        subjects_data = []
        raw_dfs = {}
        mappings = {}
        clean_dfs = {}
        for s_name, s_df in sample_dict.items():
            mapping = auto_map_columns(s_df.columns)
            analysis = analyze_subject(s_df, s_name, mapping=mapping)
            subjects_data.append(analysis)
            raw_dfs[s_name] = s_df
            mappings[s_name] = mapping
            clean_dfs[s_name] = s_df
        st.session_state['subjects_data'] = subjects_data
        st.session_state['raw_dfs'] = raw_dfs
        st.session_state['mappings'] = mappings
        st.session_state['clean_dfs'] = clean_dfs
        st.success("✅ Cargadas 5 asignaturas de ejemplo con éxito.")

    st.markdown("---")
    st.caption("Desarrollado para la Dirección de Departamento y Comisión de Calidad.")

# Process Uploaded Files if provided
if uploaded_files:
    subjects_data = []
    raw_dfs = {}
    mappings = {}
    clean_dfs = {}
    for f in uploaded_files:
        try:
            df_clean, mapping, s_name, raw_df = load_and_clean_file(f)
            analysis = analyze_subject(df_clean, s_name, mapping=mapping)
            subjects_data.append(analysis)
            raw_dfs[s_name] = raw_df
            mappings[s_name] = mapping
            clean_dfs[s_name] = df_clean
        except Exception as e:
            st.error(f"Error procesando el archivo '{getattr(f, 'name', 'desconocido')}': {e}")
    st.session_state['subjects_data'] = subjects_data
    st.session_state['raw_dfs'] = raw_dfs
    st.session_state['mappings'] = mappings
    st.session_state['clean_dfs'] = clean_dfs

# Header Section
st.markdown('<div class="main-header">Sistema de Analítica Académica y Auditoría Pedagógica</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Evaluación masiva de asignaturas y desglose estadístico por cada actividad evaluativa (alumnos presentados > 0)</div>', unsafe_allow_html=True)

# Main Application Layout
subjects_data = st.session_state.get('subjects_data', [])

if not subjects_data:
    st.info("👈 Por favor, **sube tus archivos Excel/CSV/ODS** en el panel lateral o pulsa en **'⚡ Cargar Datos de Ejemplo'** para explorar el sistema.")
    st.markdown("""
    ### ℹ️ Estructura Esperada por Archivo
    Cada archivo cargado representa una asignatura de la titulación. Se identifican automáticamente las siguientes columnas:
    - **ACT.01.CO, ACT.02.CO, ACT.03.CO, ACT.04.CO** *(Actividades de Evaluación Continua 1 a 4)*
    - **Total Prueba final parte 1, Total Prueba final parte 2** *(Examen Final - Partes 1 y 2)*
    - **Resultado de evaluación continua** *(Nota global continua)*
    - **Resultado pruebas de evaluación final** *(Nota global examen)*
    - **Nota final convocatoria ordinaria** *(Calificación final asignatura)*
    """)
else:
    # Degree-wide Consolidation
    degree_analysis = consolidate_degree_analysis(subjects_data)

    # Top Tabs
    tab_global, tab_detail, tab_data, tab_reports = st.tabs([
        "🏛️ Vista Global de Titulación",
        "📘 Análisis por Asignatura & Actividades",
        "📥 Procesamiento y Archivos",
        "📄 Exportación de Informes"
    ])

    # =========================================================================
    # TAB 1: VISTA GLOBAL DE TITULACIÓN
    # =========================================================================
    with tab_global:
        st.subheader("🏛️ Cuadro de Mando Consolidado de la Titulación")
        st.markdown('<div class="filter-badge">ℹ️ <b>Nota Metodológica:</b> Las estadísticas descriptivas se calculan exclusivamente sobre los estudiantes presentados (notas > 0.0), excluyendo no presentados para medir el rendimiento pedagógico real del grupo.</div>', unsafe_allow_html=True)

        # Top KPI Cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric(
                "Asignaturas",
                degree_analysis["tot_subjects"],
                help="Número total de asignaturas procesadas en el análisis consolidado de la titulación."
            )
        with col2:
            st.metric(
                "Alumnos Evaluados",
                degree_analysis["tot_evaluated"],
                help="Suma total de matrículas evaluadas (estudiantes con al menos una calificación > 0 en continua o examen)."
            )
        with col3:
            st.metric(
                "% Aprobados Medio",
                f"{degree_analysis['avg_pass_rate']}%",
                help="Tasa promedio de éxito académico (% de alumnos evaluados con nota final >= 5.0)."
            )
        with col4:
            st.metric(
                "Nota Media Final",
                degree_analysis["avg_final_grade"],
                help="Calificación media global obtenida por los estudiantes presentados (> 0.0) en el conjunto de materias."
            )
        with col5:
            st.metric(
                "r Medio (Cont, Exam)",
                degree_analysis["avg_r_cont_exam"],
                help="Coeficiente de correlación de Pearson promedio entre la Evaluación Continua y el Examen Final para alumnos evaluados."
            )

        st.markdown("---")

        # Comparative Table
        st.markdown("### 📊 Tabla Comparativa por Asignatura")
        summary_df = degree_analysis['summary_df']
        if not summary_df.empty:
            gradient_col = 'Media Final (presentados)' if 'Media Final (presentados)' in summary_df.columns else 'Media Final'
            st.dataframe(
                summary_df.style.background_gradient(cmap='Blues', subset=['% Aprobados (eval)', gradient_col])
                                 .highlight_between(left=-1.0, right=0.2, subset=['r(Cont, Exam)'], color='#FEE2E2')
                                 .set_properties(**{'color': '#000000'}),
                use_container_width=True,
                height=230
            )

        with st.expander("❓ **Guía Completa para Profesores: ¿Cómo interpretar el Cuadro de Mando de Titulación?**"):
            st.markdown(r"""
            ### 📌 Guía de Evaluación del Plan de Estudios
            Esta tabla cruza los datos de todas las asignaturas para evaluar el equilibrio pedagógico de la titulación:

            - **Media Continua vs Media Examen (Diferencia):** Muestra el salto entre las notas intermedias y el examen final.
              - *Brecha idónea ($0.0$ a $1.5$ ptos):* La evaluación continua capacita adecuadamente para superar el examen final.
              - *Brecha elevada ($> 2.5$ ptos):* Alerta de **inflación en continua** (actividades benévolas o sin verificación de autoría individual).
            - **Desviación Típica (σ < 1.0):** Alerta automática si la dispersión es menor a 1.0, indicando **excesiva homogeneidad** o posible falta de discriminación en los exámenes.
            - **r(Cont, Exam) - Correlación de Pearson:** Mide la capacidad de la continua para predecir el éxito en el examen:
              - 🟢 **$r \ge 0.60$ (Excelente):** Los alumnos con buena continua aprueban el examen. La continua es un diagnóstico fiel del aprendizaje.
              - 🟡 **$0.30 \le r < 0.60$ (Moderada):** Coherencia aceptable pero con margen de perfeccionamiento en las rúbricas.
              - 🔴 **$r < 0.30$ o Negativa ($r < 0$):** Incoherencia pedagógica grave. La evaluación continua no prepara al alumno para la prueba final.
            - **Nivel de Riesgo:** Clasificación automática de la materia (**Bajo, Medio, Crítico**) según tasa de suspensos, desalineación evaluativa e excesiva homogeneidad.
            """)

        st.markdown("---")

        # Comparative Visualizations
        if not summary_df.empty:
            c_left, c_right = st.columns(2)

            with c_left:
                st.markdown("#### Tasa de Aprobados por Asignatura (%)")
                fig_pass = px.bar(
                    summary_df,
                    x='Asignatura',
                    y='% Aprobados (eval)',
                    color='Nivel Riesgo',
                    color_discrete_map={'Bajo': '#10B981', 'Medio': '#F59E0B', 'Crítico': '#EF4444'},
                    text='% Aprobados (eval)',
                    title="Tasa de Éxito por Materia (% de Aprobados)"
                )
                fig_pass.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Límite 50%")
                st.plotly_chart(fig_pass, use_container_width=True)

            with c_right:
                st.markdown("#### Comparación: Nota Media Continua vs Examen (Presentados)")
                fig_comp = bg.Figure()
                fig_comp.add_trace(bg.Bar(x=summary_df['Asignatura'], y=summary_df['Media Continua'], name='Media Continua', marker_color='#3B82F6'))
                fig_comp.add_trace(bg.Bar(x=summary_df['Asignatura'], y=summary_df['Media Examen'], name='Media Examen', marker_color='#F59E0B'))
                fig_comp.update_layout(barmode='group', title="Medias de Evaluación Continua vs Examen Final (Sin Ceros)", yaxis_title="Nota (0-10)")
                st.plotly_chart(fig_comp, use_container_width=True)

        st.markdown("---")

        # Curriculum Anomalies Section
        st.markdown("### ⚠️ Auditoría de Asignaturas Anómalas en el Plan de Estudios")
        anom_df = degree_analysis['anomalies_df']
        if not anom_df.empty:
            for _, r in anom_df.iterrows():
                st.markdown(f"""
                <div class="alert-critical">
                    <b>[ANOMALÍA DETECTADA] {r['Asignatura']} — {r['Tipo Anomalía']}</b><br/>
                    {r['Detalle']}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ No se detectaron anomalías severas de evaluación en la titulación.")

    # =========================================================================
    # TAB 2: ANÁLISIS DETALLADO POR ASIGNATURA & ACTIVIDADES
    # =========================================================================
    with tab_detail:
        st.subheader("📘 Análisis Individual y Desglose Estadístico por Actividad")

        subject_names = [s['subject_name'] for s in subjects_data]
        selected_subj_name = st.selectbox("Selecciona la asignatura a inspeccionar:", subject_names)
        
        selected_analysis = next((s for s in subjects_data if s['subject_name'] == selected_subj_name), subjects_data[0])
        selected_df = st.session_state.get('clean_dfs', {}).get(selected_subj_name, st.session_state.get('raw_dfs', {}).get(selected_subj_name, pd.DataFrame()))

        # Subject KPI Summary
        k1, k2, k3, k4, k5, k6 = st.columns(6)
        k1.metric("Matriculados", selected_analysis['total_enrolled'], help="Total de alumnos matriculados.")
        k2.metric("Evaluados", selected_analysis['num_evaluated'], help="Alumnos con al menos una calificación > 0.")
        k3.metric("% Aprobados", f"{selected_analysis['pct_passed_eval']}%", help="% de aprobados sobre evaluados.")
        k4.metric("Media Final", selected_analysis['stats_final']['mean'], help="Nota media final de alumnos presentados (> 0.0).")
        k5.metric("Desv. Típica (σ)", selected_analysis['stats_final']['std'], help="Dispersión del grupo. Alerta si σ < 1.0 (excesiva homogeneidad).")
        k6.metric("r (Cont, Exam)", selected_analysis['r_cont_exam'], help="Correlación continua vs examen.")

        # Full Teacher's Guide Expander (Simplified without Q1/Q3/Skewness)
        with st.expander("❓ **Guía Completa para Profesores: Interpretación de Conceptos Estadísticos Simplificada**"):
            st.markdown(r"""
            ### 📌 Guía de Interpretación de Conceptos Estadísticos

            1. **Media vs. Mediana (P50):**
               - **Media:** Promedio aritmético de las calificaciones obtenidas por los estudiantes que han entregado o realizado la prueba ($>0$).
               - **Mediana (Percentil 50):** Nota del estudiante situado exactamente en el centro de la distribución. Si la media es muy inferior a la mediana, indica que hay un grupo pequeño con notas bajas que arrastra el promedio.

            2. **Desviación Típica ($\sigma$) y Alerta de Homogeneidad Excesiva:**
               - Mide el grado de dispersión u heterogeneidad de las notas:
                 - ⚠️ **$\sigma < 1.0$ (Excesiva Homogeneidad):** **¡ALERTA AUTOMÁTICA!** Las notas están demasiado agrupadas alrededor de la media. Sugiere falta de capacidad discriminatoria en los exámenes o evaluaciones excesivamente uniformes.
                 - **$1.0 \le \sigma \le 2.0$:** Dispersión idónea y equilibrada.
                 - **$\sigma > 2.0$:** Grupo muy heterogéneo (fuerte polarización entre alumnos excelentes y rezagados).

            3. **Efecto Suelo (% notas < 5.0) y Efecto Techo (% notas >= 9.0):**
               - **Efecto Suelo (% de notas $< 5.0$):** Señala el porcentaje de alumnos que suspenden cada prueba sobre el total de entregados. ⚠️ Se resalta en **color amarillo** cuando supera el **20.0%**.
               - **Efecto Techo (% de notas $\ge 9.0$):** Señala el porcentaje de calificaciones sobresalientes en la prueba. ⚠️ Se resalta en **color amarillo** cuando supera el **20.0%**.

            4. **Correlación de Pearson ($r$):**
               - Mide la alineación diagnóstica entre la evaluación continua y el examen final:
                 - **$r > 0.60$:** Excelente alineación; el trabajo constante durante el curso capacita al estudiante para aprobar la prueba final.
                 - **$r < 0.30$:** Desconexión metodológica. La calificación continua no es predictiva del dominio demostrado en el examen.

            5. **Inflación de Continua (Casos Discrepantes):**
               - Se identifica cuando un estudiante obtiene una **continua elevada ($\ge 7.0$)** pero **suspende gravemente el examen final ($< 4.0$)**.

            6. **Exclusión de Ceros y No Presentados:**
               - Se excluyen automáticamente las notas de `0.0` o celdas vacías para evaluar exclusivamente a los estudiantes activos.
            """)

        st.markdown("---")

        # SECTION 1: DETAILED STATISTICAL TABLE PER ACTIVITY
        st.markdown("### 📐 1. Tabla de Estadísticos Descriptivos por Actividad y Prueba (Simplificada)")
        st.caption("Desglose simplificado con Media, Mediana, Desviación Típica, Mínimo, Máximo, Efectos Suelo/Techo y Correlación.")

        act_stats_df = selected_analysis.get('activity_stats_df', pd.DataFrame())

        if not act_stats_df.empty:
            mean_col = 'Media' if 'Media' in act_stats_df.columns else act_stats_df.columns[3]
            suelo_col = 'Efecto Suelo (<5)' if 'Efecto Suelo (<5)' in act_stats_df.columns else ('Efecto Suelo (<1)' if 'Efecto Suelo (<1)' in act_stats_df.columns else act_stats_df.columns[8])
            techo_col = 'Efecto Techo (>=9)' if 'Efecto Techo (>=9)' in act_stats_df.columns else act_stats_df.columns[9]

            st.dataframe(
                act_stats_df.style.background_gradient(cmap='YlGnBu', subset=[mean_col])
                                   .highlight_between(left=7.01, right=10.0, subset=[mean_col], color='#DCFCE7')
                                   .highlight_between(left=0.0, right=4.99, subset=[mean_col], color='#FEE2E2')
                                   .highlight_between(left=0.0, right=0.99, subset=['Desviacion Tipica'], color='#FEF3C7')
                                   .highlight_between(left=20.01, right=100.0, subset=[suelo_col], color='#FEF3C7')
                                   .highlight_between(left=20.01, right=100.0, subset=[techo_col], color='#FEF3C7')
                                   .set_properties(**{'color': '#000000'}),
                use_container_width=True,
                height=340
            )

        st.markdown("---")

        # SECTION 2: COMPARATIVE BOXPLOT FOR ALL ACTIVITIES
        st.markdown("### 📦 2. Comparativa Visual de Distribución por Actividades (Solo Notas > 0)")
        st.caption("Visualización de Cajas y Bigotes mostrando la mediana y rango de notas de los alumnos que entregaron cada tarea.")

        cur_subj_mapping = st.session_state.get('mappings', {}).get(selected_subj_name, {})
        
        eval_cols_map = {}
        for key in ['ACT_01', 'ACT_02', 'ACT_03', 'ACT_04', 'EXAM_P1', 'EXAM_P2']:
            std_col_name = STANDARD_COLUMNS[key]
            if cur_subj_mapping and cur_subj_mapping.get(key):
                raw_n = str(cur_subj_mapping[key])
                if len(raw_n) > 40:
                    match = re.search(r'ACT\.\d+\.CO', raw_n, re.IGNORECASE)
                    if match:
                        act_c = match.group(0).upper()
                        r_clean = re.sub(r'^(?:Cuestionario|Tarea|Foro|Actividad):', '', raw_n, flags=re.IGNORECASE).strip()
                        r_clean = re.sub(r'\(Real\)$', '', r_clean).strip()
                        label_n = r_clean if len(r_clean) <= 30 else f"{act_c}: {r_clean[:25]}..."
                    else:
                        label_n = raw_n[:35] + '...'
                else:
                    label_n = raw_n
                eval_cols_map[std_col_name] = label_n
            else:
                defaults = {
                    'ACT_01': 'ACT.01.CO', 'ACT_02': 'ACT.02.CO', 'ACT_03': 'ACT.03.CO', 'ACT_04': 'ACT.04.CO',
                    'EXAM_P1': 'Examen Parte 1', 'EXAM_P2': 'Examen Parte 2'
                }
                eval_cols_map[std_col_name] = defaults[key]
        
        present_cols = [c for c in eval_cols_map.keys() if c in selected_df.columns and (pd.to_numeric(selected_df[c], errors='coerce') > 0.0).any()]

        if len(present_cols) > 0:
            melt_df = selected_df.melt(
                id_vars=['STUDENT_ID'],
                value_vars=present_cols,
                var_name='Prueba_Raw',
                value_name='Nota'
            ).dropna()
            
            melt_df['Nota'] = pd.to_numeric(melt_df['Nota'], errors='coerce')
            melt_df = melt_df[melt_df['Nota'] > 0.0]
            melt_df['Prueba'] = melt_df['Prueba_Raw'].map(eval_cols_map)

            fig_box_act = px.box(
                melt_df,
                x='Prueba',
                y='Nota',
                color='Prueba',
                points='all',
                hover_data=['STUDENT_ID'],
                title="Distribución y Dispersión Comparativa (Notas > 0.0)"
            )
            fig_box_act.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="Corte Aprobado (5.0)")
            fig_box_act.update_layout(yaxis_range=[0.0, 10.5], showlegend=False)
            st.plotly_chart(fig_box_act, use_container_width=True)

        st.markdown("---")

        # SECTION 3: INDIVIDUAL ACTIVITY DRILL-DOWN INSPECTOR
        st.markdown("### 🔍 3. Inspector Individual de Actividades (Drill-Down)")
        st.caption("Selecciona cualquier actividad para inspeccionar en detalle el histograma de calificaciones de los alumnos presentados.")

        act_options = [label for k_std, label in eval_cols_map.items() if k_std in selected_df.columns and (pd.to_numeric(selected_df[k_std], errors='coerce') > 0.0).any()]
        if act_options:
            selected_act_label = st.selectbox("Selecciona la actividad a inspeccionar:", act_options)
            selected_act_col = [k_std for k_std, label in eval_cols_map.items() if label == selected_act_label][0]
            
            raw_series = pd.to_numeric(selected_df[selected_act_col], errors='coerce').dropna()
            act_series = raw_series[raw_series > 0.0]

            if len(act_series) > 0:
                act_m1, act_m2, act_m3, act_m4, act_m5, act_m6 = st.columns(6)
                act_m1.metric("Entregados (> 0)", len(act_series))
                act_m2.metric("Media", round(float(act_series.mean()), 2))
                act_m3.metric("Mediana (P50)", round(float(act_series.median()), 2))
                act_m4.metric("Desv. Típica (σ)", round(float(act_series.std()), 2) if len(act_series) > 1 else 0.0)
                act_m5.metric("Mín / Máx", f"{round(float(act_series.min()), 1)} / {round(float(act_series.max()), 1)}")
                
                valid_pairs = selected_df[[selected_act_col, STANDARD_COLUMNS['NOTA_FINAL']]].dropna()
                valid_pairs = valid_pairs[(pd.to_numeric(valid_pairs[selected_act_col], errors='coerce') > 0.0) & (pd.to_numeric(valid_pairs[STANDARD_COLUMNS['NOTA_FINAL']], errors='coerce') > 0.0)]
                r_act_fin = round(float(valid_pairs.corr().iloc[0, 1]), 2) if len(valid_pairs) > 2 else 0.0
                act_m6.metric("r c/ Nota Final", r_act_fin)

                fig_act_hist = px.histogram(
                    act_series,
                    nbins=15,
                    labels={'value': f'Nota en {selected_act_label}', 'count': 'Número de Alumnos'},
                    title=f"Distribución de Calificaciones en: {selected_act_label} (Solo Entregados > 0)",
                    color_discrete_sequence=['#2563EB']
                )
                fig_act_hist.add_vline(x=5.0, line_dash="dash", line_color="red", annotation_text="Aprobado (5.0)")
                st.plotly_chart(fig_act_hist, use_container_width=True)
            else:
                st.warning(f"No hay entregas con nota > 0 para la actividad {selected_act_label}.")

        st.markdown("---")

        # SECTION 4: ALERTS AND DISCREPANCIES
        if selected_analysis.get('alerts'):
            st.markdown("#### 🚨 Alertas Pedagógicas e Indicadores de Riesgo")
            for alert in selected_analysis['alerts']:
                css_class = "alert-critical" if alert['type'] == 'CRITICAL' else "alert-warning" if alert['type'] == 'WARNING' else "alert-success"
                st.markdown(f'<div class="{css_class}"><b>[{alert["title"]}]</b><br/>{alert["message"]}</div>', unsafe_allow_html=True)

        st.markdown("#### ⚠️ Casos Atípicos e Inflación de Evaluación Continua")
        disc_df = selected_analysis.get('discrepancies_df', pd.DataFrame())
        if not disc_df.empty:
            st.warning(f"Se han identificado **{len(disc_df)} estudiantes** con desajuste severo entre continua y examen.")
            st.dataframe(disc_df, use_container_width=True)
        else:
            st.success("✅ No se detectaron casos de inflación continua o desajustes graves en esta asignatura.")

    # =========================================================================
    # TAB 3: PROCESAMIENTO Y ARCHIVOS
    # =========================================================================
    with tab_data:
        st.subheader("📥 Gestión de Archivos y Mapeo Manual de Columnas")
        st.markdown("A continuación se muestra la vista previa de datos y el **mapeo de columnas detectado automáticamente**. Si tu archivo utiliza nombres de columna no estándar, puedes ajustar manualmente los campos a continuación:")

        for i, subj in enumerate(st.session_state.get('subjects_data', [])):
            s_name = subj['subject_name']
            raw_df = st.session_state.get('raw_dfs', {}).get(s_name, pd.DataFrame())
            cur_mapping = st.session_state.get('mappings', {}).get(s_name, {})

            with st.expander(f"📄 Asignatura: {s_name} ({len(raw_df)} registros)", expanded=(i==0)):
                col_prev, col_map = st.columns([1, 1])

                with col_prev:
                    st.markdown("**Vista Previa del Archivo Original:**")
                    st.dataframe(raw_df.head(10), use_container_width=True)

                with col_map:
                    st.markdown("**🔧 Configuración del Mapeo de Columnas:**")
                    st.caption("Verifica o ajusta qué columna de tu archivo corresponde a cada campo académico:")

                    raw_col_options = [" [No asignada / Excluida] "] + list(raw_df.columns)
                    updated_mapping = {}

                    key_labels = [
                        ('STUDENT_ID', '🆔 ID / Nombre Estudiante:'),
                        ('ACT_01', '📝 Actividad Continua 1 (ACT.01):'),
                        ('ACT_02', '📝 Actividad Continua 2 (ACT.02):'),
                        ('ACT_03', '📝 Actividad Continua 3 (ACT.03):'),
                        ('ACT_04', '📝 Actividad Continua 4 (ACT.04):'),
                        ('EXAM_P1', '✍️ Examen Final - Parte 1:'),
                        ('EXAM_P2', '✍️ Examen Final - Parte 2:'),
                        ('CONTINUA', '📊 Nota Global Evaluacion Continua:'),
                        ('EXAM_FINAL', '📊 Nota Global Examen Final:'),
                        ('NOTA_FINAL', '🎓 Nota Final Convocatoria Ordinaria:')
                    ]

                    for key, label in key_labels:
                        curr_val = cur_mapping.get(key)
                        default_idx = raw_col_options.index(curr_val) if curr_val in raw_col_options else 0
                        sel_val = st.selectbox(
                            label,
                            raw_col_options,
                            index=default_idx,
                            key=f"map_{s_name}_{key}"
                        )
                        updated_mapping[key] = None if sel_val == " [No asignada / Excluida] " else sel_val

                    if st.button(f"🔄 Recalcular Análisis de '{s_name}'", key=f"btn_recalc_{s_name}", use_container_width=True):
                        new_clean_df = clean_dataframe_from_mapping(raw_df, updated_mapping, s_name)
                        new_analysis = analyze_subject(new_clean_df, s_name, mapping=updated_mapping)
                        
                        st.session_state['mappings'][s_name] = updated_mapping
                        st.session_state['clean_dfs'][s_name] = new_clean_df
                        st.session_state['raw_dfs'][s_name] = raw_df
                        
                        sd_list = st.session_state['subjects_data']
                        for idx_s, s_item in enumerate(sd_list):
                            if s_item['subject_name'] == s_name:
                                sd_list[idx_s] = new_analysis
                                break
                        st.session_state['subjects_data'] = sd_list
                        st.success(f"✅ ¡Mapeo de '{s_name}' actualizado y recalculado correctamente!")
                        st.rerun()

    # =========================================================================
    # TAB 4: EXPORTACIÓN DE INFORMES
    # =========================================================================
    with tab_reports:
        st.subheader("📄 Generación y Exportación de Informes Auditoría")

        exp_col1, exp_col2 = st.columns(2)

        with exp_col1:
            st.markdown("### 📘 Informe Individual por Asignatura")
            sel_rep_subj = st.selectbox("Selecciona la asignatura a exportar:", [s['subject_name'] for s in subjects_data], key="exp_subj_sel")
            rep_analysis = next((s for s in subjects_data if s['subject_name'] == sel_rep_subj), subjects_data[0])

            subj_pdf = generate_subject_pdf(rep_analysis)
            subj_md = generate_subject_markdown(rep_analysis)

            st.download_button(
                label=f"📥 Descargar Informe PDF ({sel_rep_subj})",
                data=subj_pdf,
                file_name=f"Informe_{sel_rep_subj}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.download_button(
                label=f"📝 Descargar Informe Markdown ({sel_rep_subj})",
                data=subj_md,
                file_name=f"Informe_{sel_rep_subj}.md",
                mime="text/markdown",
                use_container_width=True
            )

        with exp_col2:
            st.markdown("### 🏛️ Informe Consolidado de Titulación")
            st.markdown("Informe completo para la Comisión de Calidad con todas las asignaturas.")

            deg_pdf = generate_degree_pdf(degree_analysis)
            deg_md = generate_degree_markdown(degree_analysis)

            st.download_button(
                label="📥 Descargar Informe PDF Titulación (Completo)",
                data=deg_pdf,
                file_name="Informe_Consolidado_Titulacion.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.download_button(
                label="📝 Descargar Informe Markdown Titulación",
                data=deg_md,
                file_name="Informe_Consolidado_Titulacion.md",
                mime="text/markdown",
                use_container_width=True
            )

        st.markdown("---")
        st.markdown("### 👁️ Vista Previa del Informe de Titulación")
        st.markdown(generate_degree_markdown(degree_analysis))
