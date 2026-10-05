import io
import datetime
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_subject_markdown(analysis: dict) -> str:
    """Generates Markdown report for an individual subject simplified without Q1/Q3 and Skewness."""
    name = analysis.get('subject_name', 'Asignatura')
    s_fin = analysis.get('stats_final', {})
    act_df = analysis.get('activity_stats_df', pd.DataFrame())

    md = []
    md.append(f"# Informe Pedagógico y Analítico de Asignatura: {name}")
    md.append(f"**Fecha de generación:** {datetime.date.today().strftime('%d/%m/%Y')}\n")
    
    md.append("## 1. Resumen Ejecutivo de Evaluación")
    md.append(f"- **Estudiantes Matriculados:** {analysis.get('total_enrolled', 0)}")
    md.append(f"- **Estudiantes Evaluados (>0):** {analysis.get('num_evaluated', 0)} ({100 - analysis.get('pct_np_total', 0):.1f}%)")
    md.append(f"- **No Presentados (NP):** {analysis.get('num_np', 0)} ({analysis.get('pct_np_total', 0)}%)")
    md.append(f"- **Aprobados:** {analysis.get('num_passed', 0)} ({analysis.get('pct_passed_eval', 0)}% de evaluados)")
    md.append(f"- **Suspensos:** {analysis.get('num_failed', 0)} ({analysis.get('pct_failed_eval', 0)}% de evaluados)")
    md.append(f"- **Nivel de Riesgo Pedagógico:** `{str(analysis.get('risk_level', 'Bajo')).upper()}`\n")

    md.append("## 2. Estadísticos Descriptivos por Actividad y Prueba")
    md.append("| Actividad / Prueba | Entregados | Media | Mediana | Desv. Tip. | Mín - Máx | Suelo (<5) | Techo (>=9) | r c/ Final | Dificultad |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    
    if not act_df.empty:
        for _, r in act_df.iterrows():
            floor_val = r.get('Efecto Suelo (<5)', r.get('Efecto Suelo (<1)', 0.0))
            ceiling_val = r.get('Efecto Techo (>=9)', 0.0)
            ent_val = r.get('Entregados', r.get('Entregados / Presentados', 0))
            med_val = r.get('Media', r.get('Media (solo entregados)', 0.0))
            std_val = r.get('Desviacion Tipica', r.get('Desv. Típica (σ)', 0.0))
            md.append(f"| {r.get('Actividad / Prueba', '')} | {ent_val} | {med_val} | {r.get('Mediana', 0.0)} | {std_val} | {r.get('Minimo', 0.0)} - {r.get('Maximo', 0.0)} | {floor_val}% | {ceiling_val}% | {r.get('r c/ Nota Final', 0.0)} | {r.get('Dificultad', '')} |")
    md.append("")

    md.append("## 3. Análisis de Correlación y Consistencia Interna")
    md.append(f"- **Desviación Típica Nota Final (σ):** `{s_fin.get('std', 0.0):.2f}`")
    md.append(f"- **Correlación Continua vs Examen:** `r = {analysis.get('r_cont_exam', 0.0):.2f}`")
    md.append(f"- **Correlación Continua vs Nota Final:** `r = {analysis.get('r_cont_final', 0.0):.2f}`")
    md.append(f"- **Correlación Examen vs Nota Final:** `r = {analysis.get('r_exam_final', 0.0):.2f}`\n")

    if analysis.get('alerts'):
        md.append("### Alertas y Diagnósticos Automáticos")
        for alert in analysis['alerts']:
            md.append(f"> **[{alert.get('type', 'INFO')}] {alert.get('title', '')}**")
            md.append(f"> {alert.get('message', '')}\n")

    md.append("## 4. Auditoría de Casos Atípicos (Outliers & Discrepancias)")
    disc_df = analysis.get('discrepancies_df', pd.DataFrame())
    if not disc_df.empty:
        md.append(f"Se han identificado **{len(disc_df)} alumnos** con discrepancias marcadas entre continua y examen:\n")
        md.append("| Estudiante ID | Tipo Discrepancia | Nota Continua | Nota Examen | Nota Final | Diagnóstico |")
        md.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
        for _, r in disc_df.iterrows():
            md.append(f"| {r.get('STUDENT_ID', '')} | {r.get('type', '')} | {r.get('continua', 0.0)} | {r.get('examen', 0.0)} | {r.get('nota_final', 0.0)} | {r.get('diagnostico', '')} |")
        md.append("")
    else:
        md.append("No se detectaron discrepancias graves entre las notas de evaluación continua y los exámenes finales.\n")

    return "\n".join(md)

def generate_degree_markdown(degree_analysis: dict) -> str:
    """Generates Markdown report for the entire Degree / Titulación."""
    deg = degree_analysis
    sum_df = deg.get('summary_df', pd.DataFrame())
    anom_df = deg.get('anomalies_df', pd.DataFrame())

    md = []
    md.append("# Informe Global de Calidad Académica de la Titulación")
    md.append(f"**Fecha de evaluación:** {datetime.date.today().strftime('%d/%m/%Y')}\n")

    md.append("## 1. Indicadores Globales del Plan de Estudios")
    md.append(f"- **Asignaturas Analizadas:** {deg.get('tot_subjects', 0)}")
    md.append(f"- **Estudiantes Totales (Matrículas acumuladas):** {deg.get('tot_students', 0)}")
    md.append(f"- **Estudiantes Evaluados (>0):** {deg.get('tot_evaluated', 0)}")
    md.append(f"- **Tasa Media de Aprobados:** {deg.get('avg_pass_rate', 0.0)}%")
    md.append(f"- **Nota Media Global:** {deg.get('avg_final_grade', 0.0)} / 10")
    md.append(f"- **Correlación Media (Continua vs Examen):** `r = {deg.get('avg_r_cont_exam', 0.0)}`\n")

    md.append("## 2. Cuadro de Mando Comparativo por Asignatura")
    md.append("| Asignatura | Matriculados | % Aprobados | Media Final | Desv. Típ. | Media Continua | Media Examen | r(Cont,Exam) | Riesgo |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    if not sum_df.empty:
        for _, r in sum_df.iterrows():
            media_fin = r.get('Media Final (presentados)', r.get('Media Final', 0.0))
            std_fin = r.get('Desv. Tip. Final', 0.0)
            md.append(f"| {r.get('Asignatura', '')} | {r.get('Matriculados', 0)} | {r.get('% Aprobados (eval)', 0.0)}% | {media_fin} | {std_fin} | {r.get('Media Continua', 0.0)} | {r.get('Media Examen', 0.0)} | {r.get('r(Cont, Exam)', 0.0)} | `{r.get('Nivel Riesgo', 'Bajo')}` |")
    md.append("")

    md.append("## 3. Detección de Asignaturas Anómalas en la Titulación")
    if not anom_df.empty:
        md.append("| Asignatura | Tipo Anomalía | Detalle Pedagógico |")
        md.append("| :--- | :--- | :--- |")
        for _, r in anom_df.iterrows():
            md.append(f"| {r.get('Asignatura', '')} | {r.get('Tipo Anomalía', '')} | {r.get('Detalle', '')} |")
        md.append("")
    else:
        md.append("No se han detectado asignaturas con desviaciones anómalas respecto al estándar de la titulación.\n")

    md.append("## 4. Dictamen Ejecutivo y Recomendaciones para la Comisión de Calidad")
    md.append("1. **Armonización de Criterios de Evaluación:** Revisar las asignaturas con alta divergencia entre evaluación continua y examen final.")
    md.append("2. **Supervisión de Evaluación Continua:** Implementar mecanismos de verificación individual en materias con sospecha de inflación de calificaciones.")
    md.append("3. **Control de Homogeneidad Excesiva (σ < 1.0):** Supervisar exámenes o materias con desviación típica inferior a 1.0 por posible falta de capacidad discriminatoria.")

    return "\n".join(md)

def generate_subject_pdf(analysis: dict) -> bytes:
    """Generates PDF report for a single subject simplified without Q1/Q3 and Skewness."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=10
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#1F2937')
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.5,
        alignment=1
    )

    elements = []

    # Header
    name = analysis.get('subject_name', 'Asignatura')
    elements.append(Paragraph(f"Informe de Evaluación Pedagógica: {name}", title_style))
    elements.append(Paragraph(f"Universidad Europea Miguel de Cervantes | Auditoría Académica - {datetime.date.today().strftime('%d/%m/%Y')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E3A8A'), spaceAfter=8))

    # Executive Summary Box
    s_fin = analysis.get('stats_final', {})
    summary_data = [
        [Paragraph('<b>Matriculados:</b>', body_style), Paragraph(str(analysis.get('total_enrolled', 0)), body_style), Paragraph('<b>% Aprobados (eval):</b>', body_style), Paragraph(f"<b>{analysis.get('pct_passed_eval', 0)}%</b>", body_style)],
        [Paragraph('<b>Evaluados (>0):</b>', body_style), Paragraph(str(analysis.get('num_evaluated', 0)), body_style), Paragraph('<b>Media Nota Final:</b>', body_style), Paragraph(f"<b>{s_fin.get('mean', 0.0)}</b>", body_style)],
        [Paragraph('<b>Desv. Típica (σ):</b>', body_style), Paragraph(f"<b>{s_fin.get('std', 0.0)}</b>", body_style), Paragraph('<b>Nivel de Riesgo:</b>', body_style), Paragraph(f"<b>{analysis.get('risk_level', 'Bajo')}</b>", body_style)]
    ]
    summary_table = Table(summary_data, colWidths=[110, 100, 130, 110])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#D1D5DB')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8))

    # Per-Activity Descriptive Stats Table
    elements.append(Paragraph("1. Estadísticos Descriptivos por Actividades y Pruebas", h2_style))
    act_df = analysis.get('activity_stats_df', pd.DataFrame())

    act_headers = ['Prueba / Actividad', 'Partic.', 'Media', 'Mediana', 'Desv. Tip.', 'Mín-Máx', 'Suelo <5', 'Techo >=9', 'r Final', 'Dificultad']
    act_rows = [[Paragraph(h, table_header_style) for h in act_headers]]

    if not act_df.empty:
        for _, r in act_df.iterrows():
            floor_val = r.get('Efecto Suelo (<5)', r.get('Efecto Suelo (<1)', 0.0))
            ceiling_val = r.get('Efecto Techo (>=9)', 0.0)
            ent_val = r.get('Entregados', r.get('Entregados / Presentados', 0))
            med_val = r.get('Media', r.get('Media (solo entregados)', 0.0))
            std_val = r.get('Desviacion Tipica', r.get('Desv. Típica (σ)', 0.0))
            act_rows.append([
                Paragraph(str(r.get('Actividad / Prueba', '')), ParagraphStyle('CellLeft', fontName='Helvetica-Bold', fontSize=6.5)),
                Paragraph(str(ent_val), table_cell_style),
                Paragraph(str(med_val), table_cell_style),
                Paragraph(str(r.get('Mediana', 0.0)), table_cell_style),
                Paragraph(str(std_val), table_cell_style),
                Paragraph(f"{r.get('Minimo', 0.0)}-{r.get('Maximo', 0.0)}", table_cell_style),
                Paragraph(f"{floor_val}%", table_cell_style),
                Paragraph(f"{ceiling_val}%", table_cell_style),
                Paragraph(str(r.get('r c/ Nota Final', 0.0)), table_cell_style),
                Paragraph(str(r.get('Dificultad', '')), table_cell_style),
            ])

    t_act = Table(act_rows, colWidths=[130, 38, 42, 42, 38, 50, 42, 42, 42, 60])
    t_act.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_act)
    elements.append(Spacer(1, 8))

    # Alerts & Correlations
    elements.append(Paragraph("2. Correlaciones y Alertas de Homogeneidad", h2_style))
    elements.append(Paragraph(f"• <b>Desviación Típica Final (σ):</b> {s_fin.get('std', 0.0):.2f}<br/>• <b>Correlación Continua vs Examen:</b> r = {analysis.get('r_cont_exam', 0.0):.2f}<br/>• <b>Correlación Continua vs Nota Final:</b> r = {analysis.get('r_cont_final', 0.0):.2f}", body_style))
    elements.append(Spacer(1, 4))

    for alert in analysis.get('alerts', []):
        bg_col = colors.HexColor('#FEE2E2') if alert.get('type') == 'CRITICAL' else colors.HexColor('#FEF3C7')
        border_col = colors.HexColor('#EF4444') if alert.get('type') == 'CRITICAL' else colors.HexColor('#F59E0B')
        alert_p = Paragraph(f"<b>[{alert.get('title', '')}]</b><br/>{alert.get('message', '')}", body_style)
        t_alert = Table([[alert_p]], colWidths=[528])
        t_alert.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg_col),
            ('BOX', (0,0), (-1,-1), 1, border_col),
            ('PADDING', (0,0), (-1,-1), 5),
        ]))
        elements.append(t_alert)
        elements.append(Spacer(1, 4))

    # Discrepancies
    disc_df = analysis.get('discrepancies_df', pd.DataFrame())
    if not disc_df.empty:
        elements.append(Paragraph("3. Casos Atípicos Detectados (Inflación / Desconexión)", h2_style))
        disc_headers = ['ID Alumno', 'Tipo Discrepancia', 'Continua', 'Examen', 'Final']
        disc_table_data = [[Paragraph(h, table_header_style) for h in disc_headers]]
        for _, r in disc_df.head(10).iterrows():
            disc_table_data.append([
                Paragraph(str(r.get('STUDENT_ID', '')), table_cell_style),
                Paragraph(str(r.get('type', '')), ParagraphStyle('Sm', fontName='Helvetica', fontSize=6.5)),
                Paragraph(str(r.get('continua', 0.0)), table_cell_style),
                Paragraph(str(r.get('examen', 0.0)), table_cell_style),
                Paragraph(str(r.get('nota_final', 0.0)), table_cell_style),
            ])
        t_disc = Table(disc_table_data, colWidths=[75, 213, 80, 80, 80])
        t_disc.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#374151')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
            ('PADDING', (0,0), (-1,-1), 3),
        ]))
        elements.append(t_disc)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def generate_degree_pdf(degree_analysis: dict) -> bytes:
    """Generates PDF report for the entire Degree / Titulación using ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=24, leftMargin=24, topMargin=30, bottomMargin=30)
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        'H2Style',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        alignment=1
    )

    elements = []

    # Title
    deg = degree_analysis
    elements.append(Paragraph("Informe Consolidado de Titulación - Auditoría Académica", title_style))
    elements.append(Paragraph(f"Universidad Europea Miguel de Cervantes | Fecha: {datetime.date.today().strftime('%d/%m/%Y')}", body_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0F172A'), spaceAfter=8))

    # Executive Summary Cards
    summary_data = [
        [Paragraph('<b>Asignaturas:</b>', body_style), Paragraph(str(deg.get('tot_subjects', 0)), body_style), Paragraph('<b>Tasa Media Aprobados:</b>', body_style), Paragraph(f"<b>{deg.get('avg_pass_rate', 0.0)}%</b>", body_style)],
        [Paragraph('<b>Estudiantes Totales:</b>', body_style), Paragraph(str(deg.get('tot_students', 0)), body_style), Paragraph('<b>Nota Media Titulación:</b>', body_style), Paragraph(f"<b>{deg.get('avg_final_grade', 0.0)}</b>", body_style)],
        [Paragraph('<b>Evaluados Totales:</b>', body_style), Paragraph(str(deg.get('tot_evaluated', 0)), body_style), Paragraph('<b>Correlación r(Cont,Exam):</b>', body_style), Paragraph(f"<b>{deg.get('avg_r_cont_exam', 0.0)}</b>", body_style)]
    ]
    t_summary = Table(summary_data, colWidths=[110, 100, 130, 110])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t_summary)
    elements.append(Spacer(1, 8))

    # Consolidated Table
    elements.append(Paragraph("1. Cuadro de Mando Comparativo por Asignatura", h2_style))
    sum_df = deg.get('summary_df', pd.DataFrame())

    deg_headers = ['Asignatura', 'Matric.', '% Aprob.', 'Media Fin.', 'σ Final', 'Media Cont.', 'Media Exam.', 'r(C,E)', 'Riesgo']
    deg_table_rows = [[Paragraph(h, table_header_style) for h in deg_headers]]

    if not sum_df.empty:
        for _, r in sum_df.iterrows():
            media_fin = r.get('Media Final (presentados)', r.get('Media Final', 0.0))
            std_fin = r.get('Desv. Tip. Final', 0.0)
            deg_table_rows.append([
                Paragraph(str(r.get('Asignatura', '')), ParagraphStyle('CellLeft', fontName='Helvetica', fontSize=7)),
                Paragraph(str(r.get('Matriculados', 0)), table_cell_style),
                Paragraph(f"{r.get('% Aprobados (eval)', 0.0)}%", table_cell_style),
                Paragraph(str(media_fin), table_cell_style),
                Paragraph(str(std_fin), table_cell_style),
                Paragraph(str(r.get('Media Continua', 0.0)), table_cell_style),
                Paragraph(str(r.get('Media Examen', 0.0)), table_cell_style),
                Paragraph(str(r.get('r(Cont, Exam)', 0.0)), table_cell_style),
                Paragraph(str(r.get('Nivel Riesgo', 'Bajo')), table_cell_style),
            ])

    t_deg = Table(deg_table_rows, colWidths=[130, 42, 48, 50, 48, 50, 50, 45, 65])
    t_deg.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_deg)
    elements.append(Spacer(1, 8))

    # Anomalies
    anom_df = deg.get('anomalies_df', pd.DataFrame())
    if not anom_df.empty:
        elements.append(Paragraph("2. Asignaturas Anómalas Detectadas", h2_style))
        anom_headers = ['Asignatura', 'Tipo Anomalía', 'Detalle']
        anom_rows = [[Paragraph(h, table_header_style) for h in anom_headers]]
        for _, r in anom_df.iterrows():
            anom_rows.append([
                Paragraph(str(r.get('Asignatura', '')), table_cell_style),
                Paragraph(str(r.get('Tipo Anomalía', '')), ParagraphStyle('Sm', fontName='Helvetica-Bold', fontSize=7)),
                Paragraph(str(r.get('Detalle', '')), ParagraphStyle('Sm', fontName='Helvetica', fontSize=7)),
            ])
        t_anom = Table(anom_rows, colWidths=[130, 150, 248])
        t_anom.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991B1B')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FECACA')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        elements.append(t_anom)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
