import numpy as np
import pandas as pd
from data_processor import STANDARD_COLUMNS

def generate_sample_subject(subject_name: str, num_students: int = 50, avg_cont: float = 7.0, avg_exam: float = 6.0, corr_factor: float = 0.6, noise_std: float = 1.2) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset for a single university subject.
    Includes both [[id]] and STUDENT_ID for compatibility.
    """
    np.random.seed(abs(hash(subject_name)) % (2**32))

    # Latent student ability (0 to 10)
    ability = np.random.normal(loc=6.0, scale=1.8, size=num_students)
    ability = np.clip(ability, 1.0, 10.0)

    # Continuous activities
    c1 = np.clip(ability * 0.8 + np.random.normal(avg_cont - 4.8, noise_std, num_students), 0.5, 10)
    c2 = np.clip(ability * 0.85 + np.random.normal(avg_cont - 5.1, noise_std, num_students), 0.5, 10)
    c3 = np.clip(ability * 0.75 + np.random.normal(avg_cont - 4.5, noise_std, num_students), 0.5, 10)
    c4 = np.clip(ability * 0.80 + np.random.normal(avg_cont - 4.8, noise_std, num_students), 0.5, 10)

    continua = np.round((c1 + c2 + c3 + c4) / 4.0, 2)

    # Exam parts
    p1 = np.clip(ability * corr_factor * 1.0 + (1 - corr_factor) * 5.0 + np.random.normal(avg_exam - 6.0, noise_std * 1.2, num_students), 0.5, 10)
    p2 = np.clip(ability * corr_factor * 1.0 + (1 - corr_factor) * 5.0 + np.random.normal(avg_exam - 6.0, noise_std * 1.2, num_students), 0.5, 10)

    exam_final = np.round((p1 + p2) / 2.0, 2)

    # Final grade: 40% continuous + 60% exam
    nota_final = np.round(continua * 0.4 + exam_final * 0.6, 2)

    # Introduce some non-presentados (NP / NaN) ~ 8%
    np_mask = np.random.rand(num_students) < 0.08

    # Introduce continuous inflation outliers
    outlier_idx = np.random.choice(num_students, size=min(3, num_students), replace=False)
    continua[outlier_idx] = np.random.uniform(8.0, 9.5, size=len(outlier_idx))
    exam_final[outlier_idx] = np.random.uniform(2.0, 3.8, size=len(outlier_idx))
    nota_final[outlier_idx] = np.round(continua[outlier_idx] * 0.4 + exam_final[outlier_idx] * 0.6, 2)

    c1[np_mask] = np.nan
    c2[np_mask] = np.nan
    c3[np_mask] = np.nan
    c4[np_mask] = np.nan
    p1[np_mask] = np.nan
    p2[np_mask] = np.nan
    continua[np_mask] = np.nan
    exam_final[np_mask] = np.nan
    nota_final[np_mask] = np.nan

    df = pd.DataFrame({
        'STUDENT_ID': [f"Estudiante_{10000 + i}" for i in range(num_students)],
        '[[id]]': [10000 + i for i in range(num_students)],
        STANDARD_COLUMNS['ACT_01']: np.round(c1, 2),
        STANDARD_COLUMNS['ACT_02']: np.round(c2, 2),
        STANDARD_COLUMNS['ACT_03']: np.round(c3, 2),
        STANDARD_COLUMNS['ACT_04']: np.round(c4, 2),
        STANDARD_COLUMNS['EXAM_P1']: np.round(p1, 2),
        STANDARD_COLUMNS['EXAM_P2']: np.round(p2, 2),
        STANDARD_COLUMNS['CONTINUA']: continua,
        STANDARD_COLUMNS['EXAM_FINAL']: exam_final,
        STANDARD_COLUMNS['NOTA_FINAL']: nota_final
    })

    return df

def generate_sample_degree() -> dict:
    """
    Generates a full degree benchmark dataset with 5 realistic subjects.
    Returns dict {subject_name: DataFrame}
    """
    subjects = {
        'Inmunología': generate_sample_subject('Inmunología', num_students=60, avg_cont=7.2, avg_exam=5.8, corr_factor=0.65),
        'Nutrición Humana y Dietética': generate_sample_subject('Nutrición Humana', num_students=55, avg_cont=7.8, avg_exam=6.9, corr_factor=0.72),
        'Bioquímica Estructural': generate_sample_subject('Bioquímica Estructural', num_students=65, avg_cont=6.5, avg_exam=4.2, corr_factor=0.25),
        'Fisiología Humana II': generate_sample_subject('Fisiología Humana II', num_students=50, avg_cont=6.8, avg_exam=5.2, corr_factor=0.55),
        'Anatomía Aplicada': generate_sample_subject('Anatomía Aplicada', num_students=70, avg_cont=8.1, avg_exam=4.5, corr_factor=0.15)
    }
    return subjects
