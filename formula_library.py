"""Built-in medical / research formula library (~90 formulas)."""

LIBRARY = [
    # ═══════════════════════════════════════════════════════
    # ANTHROPOMETRIC
    # ═══════════════════════════════════════════════════════
    {"id":"bmi","name":"Body Mass Index","abbr":"BMI","category":"Anthropometric",
     "description":"Body mass relative to height.",
     "inputs":[{"key":"weight","label":"Weight","unit":"kg"},
               {"key":"height","label":"Height","unit":"m"}],
     "expression":"weight / (height * height)","unit":"kg/m²",
     "reference":"<18.5 under · 18.5–24.9 normal · 25–29.9 over · ≥30 obese","source":"WHO"},

    {"id":"bsa_dubois","name":"Body Surface Area (Du Bois)","abbr":"BSA","category":"Anthropometric",
     "description":"Classic BSA formula.",
     "inputs":[{"key":"weight","label":"Weight","unit":"kg"},
               {"key":"height","label":"Height","unit":"cm"}],
     "expression":"0.007184 * (height ** 0.725) * (weight ** 0.425)","unit":"m²",
     "reference":"~1.7–2.0 m² adult","source":"Du Bois 1916"},

    {"id":"bsa_mosteller","name":"Body Surface Area (Mosteller)","abbr":"BSA","category":"Anthropometric",
     "description":"Simple, widely used BSA.",
     "inputs":[{"key":"weight","label":"Weight","unit":"kg"},
               {"key":"height","label":"Height","unit":"cm"}],
     "expression":"sqrt(height * weight / 3600)","unit":"m²",
     "reference":"~1.7–2.0 m²","source":"Mosteller 1987"},

    {"id":"ibw_male","name":"Ideal Body Weight (Male)","abbr":"IBW","category":"Anthropometric",
     "description":"Devine formula, males.",
     "inputs":[{"key":"height_in","label":"Height","unit":"inches"}],
     "expression":"50 + 2.3 * (height_in - 60)","unit":"kg","reference":"—","source":"Devine 1974"},

    {"id":"ibw_female","name":"Ideal Body Weight (Female)","abbr":"IBW","category":"Anthropometric",
     "description":"Devine formula, females.",
     "inputs":[{"key":"height_in","label":"Height","unit":"inches"}],
     "expression":"45.5 + 2.3 * (height_in - 60)","unit":"kg","reference":"—","source":"Devine 1974"},

    {"id":"adj_bw","name":"Adjusted Body Weight","abbr":"ABW","category":"Anthropometric",
     "description":"For drug dosing in obesity.",
     "inputs":[{"key":"ibw","label":"Ideal body weight","unit":"kg"},
               {"key":"actual","label":"Actual weight","unit":"kg"}],
     "expression":"ibw + 0.4 * (actual - ibw)","unit":"kg","reference":"—","source":"—"},

    {"id":"whtr","name":"Waist-to-Height Ratio","abbr":"WHtR","category":"Anthropometric",
     "description":"Central obesity marker.",
     "inputs":[{"key":"waist","label":"Waist","unit":"cm"},
               {"key":"height","label":"Height","unit":"cm"}],
     "expression":"waist / height","unit":"ratio","reference":"<0.5 desirable","source":"Ashwell 2011"},

    {"id":"whr","name":"Waist-to-Hip Ratio","abbr":"WHR","category":"Anthropometric",
     "description":"Fat distribution.",
     "inputs":[{"key":"waist","label":"Waist","unit":"cm"},
               {"key":"hip","label":"Hip","unit":"cm"}],
     "expression":"waist / hip","unit":"ratio",
     "reference":"Male <0.9 · Female <0.85","source":"WHO"},

    {"id":"ponderal","name":"Ponderal Index","abbr":"PI","category":"Anthropometric",
     "description":"Weight relative to cubed height.",
     "inputs":[{"key":"weight","label":"Weight","unit":"kg"},
               {"key":"height","label":"Height","unit":"m"}],
     "expression":"weight / (height ** 3)","unit":"kg/m³","reference":"—","source":"Rohrer"},

    {"id":"bri","name":"Body Roundness Index","abbr":"BRI","category":"Anthropometric",
     "description":"Better obesity marker than BMI.",
     "inputs":[{"key":"waist","label":"Waist","unit":"cm"},
               {"key":"height","label":"Height","unit":"cm"}],
     "expression":"364.2 - 365.5 * sqrt(1 - ((waist / (2 * pi)) ** 2) / ((0.5 * height) ** 2))",
     "unit":"—","reference":"<3.4 normal","source":"Thomas 2013"},

    {"id":"conicity","name":"Conicity Index","abbr":"CI","category":"Anthropometric",
     "description":"Abdominal fat accumulation.",
     "inputs":[{"key":"waist","label":"Waist","unit":"m"},
               {"key":"weight","label":"Weight","unit":"kg"},
               {"key":"height","label":"Height","unit":"m"}],
     "expression":"waist / (0.109 * sqrt(weight / height))","unit":"—",
     "reference":"~1.15–1.25","source":"Valdez 1993"},

    # ═══════════════════════════════════════════════════════
    # METABOLIC / DIABETES
    # ═══════════════════════════════════════════════════════
    {"id":"homa_ir","name":"HOMA-IR","abbr":"HOMA-IR","category":"Metabolic",
     "description":"Homeostasis Model Assessment of Insulin Resistance.",
     "inputs":[{"key":"fins","label":"Fasting insulin","unit":"μU/mL"},
               {"key":"fpg","label":"Fasting glucose","unit":"mg/dL"}],
     "expression":"(fins * fpg) / 405","unit":"—",
     "reference":"<2.0 normal · ≥2.5 IR","source":"Matthews 1985"},

    {"id":"homa_ir_si","name":"HOMA-IR (SI units)","abbr":"HOMA-IR","category":"Metabolic",
     "description":"HOMA-IR using mmol/L glucose.",
     "inputs":[{"key":"fins","label":"Fasting insulin","unit":"mU/L"},
               {"key":"fpg","label":"Fasting glucose","unit":"mmol/L"}],
     "expression":"(fins * fpg) / 22.5","unit":"—","reference":"<2.0","source":"Matthews 1985"},

    {"id":"homa_b","name":"HOMA-B (β-cell function)","abbr":"HOMA-β","category":"Metabolic",
     "description":"β-cell function estimate.",
     "inputs":[{"key":"fins","label":"Fasting insulin","unit":"μU/mL"},
               {"key":"fpg","label":"Fasting glucose","unit":"mmol/L"}],
     "expression":"(20 * fins) / (fpg - 3.5)","unit":"%","reference":"~100%","source":"Matthews 1985"},

    {"id":"quicki","name":"QUICKI","abbr":"QUICKI","category":"Metabolic",
     "description":"Quantitative Insulin Sensitivity Check Index.",
     "inputs":[{"key":"fins","label":"Fasting insulin","unit":"μU/mL"},
               {"key":"fpg","label":"Fasting glucose","unit":"mg/dL"}],
     "expression":"1 / (log10(fins) + log10(fpg))","unit":"—",
     "reference":">0.45 normal","source":"Katz 2000"},

    {"id":"fgir","name":"Fasting Glucose-to-Insulin Ratio","abbr":"FGIR","category":"Metabolic",
     "description":"Simple insulin sensitivity proxy.",
     "inputs":[{"key":"fpg","label":"Fasting glucose","unit":"mg/dL"},
               {"key":"fins","label":"Fasting insulin","unit":"μU/mL"}],
     "expression":"fpg / fins","unit":"—","reference":">4.5 normal","source":"—"},

    {"id":"igi","name":"Insulinogenic Index","abbr":"IGI","category":"Metabolic",
     "description":"Early-phase insulin secretion.",
     "inputs":[{"key":"dins","label":"Δ Insulin (30 min)","unit":"μU/mL"},
               {"key":"dglu","label":"Δ Glucose (30 min)","unit":"mg/dL"}],
     "expression":"dins / dglu","unit":"—","reference":"≥0.4 normal","source":"Seltzer 1967"},

    {"id":"matsuda","name":"Matsuda Index (approx)","abbr":"ISI","category":"Metabolic",
     "description":"Whole-body insulin sensitivity from OGTT.",
     "inputs":[{"key":"fpg","label":"Fasting glucose","unit":"mg/dL"},
               {"key":"fins","label":"Fasting insulin","unit":"μU/mL"},
               {"key":"mpg","label":"Mean OGTT glucose","unit":"mg/dL"},
               {"key":"mins","label":"Mean OGTT insulin","unit":"μU/mL"}],
     "expression":"10000 / sqrt(fpg * fins * mpg * mins)","unit":"—",
     "reference":">2.5 normal","source":"Matsuda 1999"},

    {"id":"tyg","name":"Triglyceride-Glucose Index","abbr":"TyG","category":"Metabolic",
     "description":"Surrogate for insulin resistance.",
     "inputs":[{"key":"tg","label":"Triglycerides","unit":"mg/dL"},
               {"key":"fpg","label":"Fasting glucose","unit":"mg/dL"}],
     "expression":"log((tg * fpg) / 2)","unit":"—",
     "reference":"<8.8 normal · ≥8.8 IR","source":"Simental-Mendía 2008"},

    {"id":"tyg_bmi","name":"TyG-BMI","abbr":"TyG-BMI","category":"Metabolic",
     "description":"Combined IR marker.",
     "inputs":[{"key":"tyg","label":"TyG index","unit":"—"},
               {"key":"bmi","label":"BMI","unit":"kg/m²"}],
     "expression":"tyg * bmi","unit":"—","reference":"—","source":"—"},

    {"id":"eag_hba1c","name":"Estimated Average Glucose","abbr":"eAG","category":"Metabolic",
     "description":"From HbA1c (%).",
     "inputs":[{"key":"hba1c","label":"HbA1c","unit":"%"}],
     "expression":"28.7 * hba1c - 46.7","unit":"mg/dL",
     "reference":"Matches lab average","source":"Nathan 2008"},

    {"id":"hba1c_ifcc","name":"HbA1c IFCC ↔ DCCT","abbr":"IFCC","category":"Metabolic",
     "description":"Convert % to mmol/mol.",
     "inputs":[{"key":"hba1c_pct","label":"HbA1c","unit":"%"}],
     "expression":"(hba1c_pct - 2.15) * 10.929","unit":"mmol/mol",
     "reference":"—","source":"IFCC"},

    # ═══════════════════════════════════════════════════════
    # LIPID / CARDIO
    # ═══════════════════════════════════════════════════════
    {"id":"ldl_friedewald","name":"LDL (Friedewald)","abbr":"LDL-C","category":"Lipid",
     "description":"Classic LDL calculation (valid TG <400 mg/dL).",
     "inputs":[{"key":"tc","label":"Total cholesterol","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"},
               {"key":"tg","label":"Triglycerides","unit":"mg/dL"}],
     "expression":"tc - hdl - (tg / 5)","unit":"mg/dL",
     "reference":"<100 optimal","source":"Friedewald 1972"},

    {"id":"non_hdl","name":"Non-HDL Cholesterol","abbr":"Non-HDL","category":"Lipid",
     "description":"Atherogenic burden.",
     "inputs":[{"key":"tc","label":"Total cholesterol","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"tc - hdl","unit":"mg/dL","reference":"<130 optimal","source":"NCEP"},

    {"id":"tc_hdl","name":"Total Cholesterol / HDL Ratio","abbr":"TC/HDL","category":"Lipid",
     "description":"Castelli Risk Index I.",
     "inputs":[{"key":"tc","label":"Total cholesterol","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"tc / hdl","unit":"—","reference":"<5.0 optimal","source":"Castelli 1983"},

    {"id":"ldl_hdl","name":"LDL / HDL Ratio","abbr":"LDL/HDL","category":"Lipid",
     "description":"Castelli Risk Index II.",
     "inputs":[{"key":"ldl","label":"LDL","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"ldl / hdl","unit":"—","reference":"<3.5","source":"Castelli 1983"},

    {"id":"tg_hdl","name":"Triglyceride / HDL Ratio","abbr":"TG/HDL","category":"Lipid",
     "description":"Insulin resistance marker.",
     "inputs":[{"key":"tg","label":"Triglycerides","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"tg / hdl","unit":"—","reference":"<3.0","source":"McLaughlin 2003"},

    {"id":"aip","name":"Atherogenic Index of Plasma","abbr":"AIP","category":"Lipid",
     "description":"Predicts cardiovascular risk.",
     "inputs":[{"key":"tg","label":"Triglycerides","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"log10(tg / hdl)","unit":"—",
     "reference":"<0.11 low · 0.11–0.21 intermediate · >0.21 high","source":"Dobiášová 2001"},

    {"id":"ac","name":"Atherogenic Coefficient","abbr":"AC","category":"Lipid",
     "description":"Non-HDL to HDL ratio.",
     "inputs":[{"key":"tc","label":"Total cholesterol","unit":"mg/dL"},
               {"key":"hdl","label":"HDL","unit":"mg/dL"}],
     "expression":"(tc - hdl) / hdl","unit":"—","reference":"<3.0","source":"—"},

    {"id":"vai_male","name":"Visceral Adiposity Index (Male)","abbr":"VAI","category":"Lipid",
     "description":"Visceral fat estimate, males.",
     "inputs":[{"key":"wc","label":"Waist","unit":"cm"},
               {"key":"bmi","label":"BMI","unit":"kg/m²"},
               {"key":"tg","label":"Triglycerides","unit":"mmol/L"},
               {"key":"hdl","label":"HDL","unit":"mmol/L"}],
     "expression":"(wc / (39.68 + 1.88 * bmi)) * (tg / 1.03) * (1.31 / hdl)",
     "unit":"—","reference":"<2.5 low risk","source":"Amato 2010"},

    {"id":"vai_female","name":"Visceral Adiposity Index (Female)","abbr":"VAI","category":"Lipid",
     "description":"Visceral fat estimate, females.",
     "inputs":[{"key":"wc","label":"Waist","unit":"cm"},
               {"key":"bmi","label":"BMI","unit":"kg/m²"},
               {"key":"tg","label":"Triglycerides","unit":"mmol/L"},
               {"key":"hdl","label":"HDL","unit":"mmol/L"}],
     "expression":"(wc / (36.58 + 1.89 * bmi)) * (tg / 0.81) * (1.52 / hdl)",
     "unit":"—","reference":"<2.5 low risk","source":"Amato 2010"},

    {"id":"lap_male","name":"Lipid Accumulation Product (Male)","abbr":"LAP","category":"Lipid",
     "description":"Visceral fat marker, males.",
     "inputs":[{"key":"wc","label":"Waist","unit":"cm"},
               {"key":"tg","label":"Triglycerides","unit":"mmol/L"}],
     "expression":"(wc - 65) * tg","unit":"—","reference":"<44.8 normal","source":"Kahn 2005"},

    {"id":"lap_female","name":"Lipid Accumulation Product (Female)","abbr":"LAP","category":"Lipid",
     "description":"Visceral fat marker, females.",
     "inputs":[{"key":"wc","label":"Waist","unit":"cm"},
               {"key":"tg","label":"Triglycerides","unit":"mmol/L"}],
     "expression":"(wc - 58) * tg","unit":"—","reference":"<31.7 normal","source":"Kahn 2005"},

    # ═══════════════════════════════════════════════════════
    # HEPATIC
    # ═══════════════════════════════════════════════════════
    {"id":"ast_alt","name":"AST/ALT Ratio (De Ritis)","abbr":"AST/ALT","category":"Hepatic",
     "description":"Differentiates liver disease types.",
     "inputs":[{"key":"ast","label":"AST","unit":"U/L"},
               {"key":"alt","label":"ALT","unit":"U/L"}],
     "expression":"ast / alt","unit":"—",
     "reference":"<1 NAFLD · >2 alcoholic hepatitis","source":"De Ritis 1957"},

    {"id":"apri","name":"AST to Platelet Ratio Index","abbr":"APRI","category":"Hepatic",
     "description":"Liver fibrosis predictor.",
     "inputs":[{"key":"ast","label":"AST","unit":"U/L"},
               {"key":"ast_uln","label":"AST upper limit normal","unit":"U/L"},
               {"key":"plt","label":"Platelets","unit":"10⁹/L"}],
     "expression":"((ast / ast_uln) * 100) / plt","unit":"—",
     "reference":"<0.5 low · >1.5 significant fibrosis","source":"Wai 2003"},

    {"id":"fib4","name":"FIB-4 Index","abbr":"FIB-4","category":"Hepatic",
     "description":"Non-invasive fibrosis score.",
     "inputs":[{"key":"age","label":"Age","unit":"yrs"},
               {"key":"ast","label":"AST","unit":"U/L"},
               {"key":"plt","label":"Platelets","unit":"10⁹/L"},
               {"key":"alt","label":"ALT","unit":"U/L"}],
     "expression":"(age * ast) / (plt * sqrt(alt))","unit":"—",
     "reference":"<1.3 low · >2.67 high risk","source":"Sterling 2006"},

    {"id":"ggt_plt","name":"GGT/Platelet Ratio","abbr":"GPR","category":"Hepatic",
     "description":"Fibrosis predictor.",
     "inputs":[{"key":"ggt","label":"GGT","unit":"U/L"},
               {"key":"plt","label":"Platelets","unit":"10⁹/L"}],
     "expression":"ggt / plt","unit":"—","reference":"—","source":"Lemoine 2014"},

    {"id":"albi","name":"ALBI Score","abbr":"ALBI","category":"Hepatic",
     "description":"Liver function in HCC.",
     "inputs":[{"key":"alb","label":"Albumin","unit":"g/L"},
               {"key":"bili","label":"Bilirubin","unit":"μmol/L"}],
     "expression":"log10(bili) * 0.66 + alb * (-0.085)","unit":"—",
     "reference":"<-2.60 grade 1","source":"Johnson 2015"},

    # ═══════════════════════════════════════════════════════
    # HEMATOLOGY / INFLAMMATION
    # ═══════════════════════════════════════════════════════
    {"id":"nlr","name":"Neutrophil-to-Lymphocyte Ratio","abbr":"NLR","category":"Hematology",
     "description":"Systemic inflammation marker.",
     "inputs":[{"key":"neut","label":"Neutrophils","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"neut / lymph","unit":"—",
     "reference":"<3 low · >3 high inflammation","source":"Zahorec 2001"},

    {"id":"plr","name":"Platelet-to-Lymphocyte Ratio","abbr":"PLR","category":"Hematology",
     "description":"Inflammation / prognosis marker.",
     "inputs":[{"key":"plt","label":"Platelets","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"plt / lymph","unit":"—","reference":"<150 normal","source":"Smith 2002"},

    {"id":"mlr","name":"Monocyte-to-Lymphocyte Ratio","abbr":"MLR","category":"Hematology",
     "description":"Chronic inflammation.",
     "inputs":[{"key":"mono","label":"Monocytes","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"mono / lymph","unit":"—","reference":"<0.3","source":"—"},

    {"id":"lrm","name":"Lymphocyte-to-Monocyte Ratio","abbr":"LMR","category":"Hematology",
     "description":"Immune status marker.",
     "inputs":[{"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"},
               {"key":"mono","label":"Monocytes","unit":"10⁹/L"}],
     "expression":"lymph / mono","unit":"—","reference":">3.0","source":"—"},

    {"id":"sii","name":"Systemic Immune-Inflammation Index","abbr":"SII","category":"Hematology",
     "description":"Combined inflammation index.",
     "inputs":[{"key":"plt","label":"Platelets","unit":"10⁹/L"},
               {"key":"neut","label":"Neutrophils","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"(plt * neut) / lymph","unit":"—","reference":"<500","source":"Hu 2014"},

    {"id":"siri","name":"Systemic Inflammation Response Index","abbr":"SIRI","category":"Hematology",
     "description":"Inflammation marker.",
     "inputs":[{"key":"neut","label":"Neutrophils","unit":"10⁹/L"},
               {"key":"mono","label":"Monocytes","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"(neut * mono) / lymph","unit":"—","reference":"<1.0","source":"Qi 2016"},

    {"id":"aisi","name":"Aggregate Index of Systemic Inflammation","abbr":"AISI","category":"Hematology",
     "description":"Composite inflammation marker.",
     "inputs":[{"key":"neut","label":"Neutrophils","unit":"10⁹/L"},
               {"key":"plt","label":"Platelets","unit":"10⁹/L"},
               {"key":"mono","label":"Monocytes","unit":"10⁹/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"(neut * plt * mono) / lymph","unit":"—","reference":"—","source":"—"},

    {"id":"pnr","name":"Platelet-to-Neutrophil Ratio","abbr":"PNR","category":"Hematology",
     "description":"Bacterial infection marker.",
     "inputs":[{"key":"plt","label":"Platelets","unit":"10⁹/L"},
               {"key":"neut","label":"Neutrophils","unit":"10⁹/L"}],
     "expression":"plt / neut","unit":"—","reference":">20 low infection","source":"—"},

    {"id":"mcv","name":"Mean Corpuscular Volume","abbr":"MCV","category":"Hematology",
     "description":"Average RBC size.",
     "inputs":[{"key":"hct","label":"Hematocrit","unit":"%"},
               {"key":"rbc","label":"RBC","unit":"10⁶/μL"}],
     "expression":"(hct * 10) / rbc","unit":"fL",
     "reference":"80–100 fL","source":"—"},

    {"id":"mch","name":"Mean Corpuscular Hemoglobin","abbr":"MCH","category":"Hematology",
     "description":"Average Hb per RBC.",
     "inputs":[{"key":"hb","label":"Hemoglobin","unit":"g/dL"},
               {"key":"rbc","label":"RBC","unit":"10⁶/μL"}],
     "expression":"(hb * 10) / rbc","unit":"pg","reference":"27–33 pg","source":"—"},

    {"id":"mchc","name":"Mean Corpuscular Hb Concentration","abbr":"MCHC","category":"Hematology",
     "description":"Hb concentration per RBC volume.",
     "inputs":[{"key":"hb","label":"Hemoglobin","unit":"g/dL"},
               {"key":"hct","label":"Hematocrit","unit":"%"}],
     "expression":"(hb * 100) / hct","unit":"g/dL","reference":"32–36 g/dL","source":"—"},

    {"id":"mentzer","name":"Mentzer Index","abbr":"MI","category":"Hematology",
     "description":"Distinguishes IDA from thalassemia.",
     "inputs":[{"key":"mcv","label":"MCV","unit":"fL"},
               {"key":"rbc","label":"RBC","unit":"10⁶/μL"}],
     "expression":"mcv / rbc","unit":"—",
     "reference":"<13 thalassemia · >13 IDA","source":"Mentzer 1973"},

    {"id":"crp_alb","name":"CRP/Albumin Ratio","abbr":"CAR","category":"Hematology",
     "description":"Inflammation-nutrition marker.",
     "inputs":[{"key":"crp","label":"CRP","unit":"mg/L"},
               {"key":"alb","label":"Albumin","unit":"g/dL"}],
     "expression":"crp / alb","unit":"—","reference":"<1.0 good","source":"Fairclough 2009"},

    {"id":"pni","name":"Prognostic Nutritional Index","abbr":"PNI","category":"Hematology",
     "description":"Nutrition + immune status.",
     "inputs":[{"key":"alb","label":"Albumin","unit":"g/L"},
               {"key":"lymph","label":"Lymphocytes","unit":"10⁹/L"}],
     "expression":"10 * alb + 0.005 * lymph * 1000","unit":"—",
     "reference":">45 normal","source":"Onodera 1984"},

    # ═══════════════════════════════════════════════════════
    # RENAL
    # ═══════════════════════════════════════════════════════
    {"id":"mdrd","name":"eGFR (MDRD)","abbr":"eGFR","category":"Renal",
     "description":"MDRD 4-variable (non-Black).",
     "inputs":[{"key":"scr","label":"Serum creatinine","unit":"mg/dL"},
               {"key":"age","label":"Age","unit":"yrs"}],
     "expression":"175 * (scr ** -1.154) * (age ** -0.203)","unit":"mL/min/1.73m²",
     "reference":">90 normal","source":"Levey 1999"},

    {"id":"mdrd_female","name":"eGFR (MDRD, Female)","abbr":"eGFR","category":"Renal",
     "description":"MDRD 4-variable, female correction.",
     "inputs":[{"key":"scr","label":"Serum creatinine","unit":"mg/dL"},
               {"key":"age","label":"Age","unit":"yrs"}],
     "expression":"175 * (scr ** -1.154) * (age ** -0.203) * 0.742",
     "unit":"mL/min/1.73m²","reference":">90","source":"Levey 1999"},

    {"id":"cockcroft","name":"Cockcroft-Gault CrCl","abbr":"CrCl","category":"Renal",
     "description":"Creatinine clearance (male).",
     "inputs":[{"key":"age","label":"Age","unit":"yrs"},
               {"key":"weight","label":"Weight","unit":"kg"},
               {"key":"scr","label":"Serum creatinine","unit":"mg/dL"}],
     "expression":"((140 - age) * weight) / (72 * scr)","unit":"mL/min",
     "reference":">90 normal","source":"Cockcroft 1976"},

    {"id":"cockcroft_f","name":"Cockcroft-Gault CrCl (Female)","abbr":"CrCl","category":"Renal",
     "description":"CrCl with female correction.",
     "inputs":[{"key":"age","label":"Age","unit":"yrs"},
               {"key":"weight","label":"Weight","unit":"kg"},
               {"key":"scr","label":"Serum creatinine","unit":"mg/dL"}],
     "expression":"((140 - age) * weight * 0.85) / (72 * scr)","unit":"mL/min",
     "reference":">90","source":"Cockcroft 1976"},

    {"id":"fena","name":"Fractional Excretion of Sodium","abbr":"FENa","category":"Renal",
     "description":"Distinguishes prerenal from intrinsic AKI.",
     "inputs":[{"key":"una","label":"Urine Na","unit":"mEq/L"},
               {"key":"pna","label":"Plasma Na","unit":"mEq/L"},
               {"key":"ucr","label":"Urine creatinine","unit":"mg/dL"},
               {"key":"pcr","label":"Plasma creatinine","unit":"mg/dL"}],
     "expression":"(una * pcr * 100) / (pna * ucr)","unit":"%",
     "reference":"<1% prerenal · >2% intrinsic","source":"Espinel 1976"},

    {"id":"feurea","name":"Fractional Excretion of Urea","abbr":"FEUrea","category":"Renal",
     "description":"FENa alternative on diuretics.",
     "inputs":[{"key":"uurea","label":"Urine urea","unit":"mg/dL"},
               {"key":"purea","label":"Plasma urea","unit":"mg/dL"},
               {"key":"ucr","label":"Urine creatinine","unit":"mg/dL"},
               {"key":"pcr","label":"Plasma creatinine","unit":"mg/dL"}],
     "expression":"(uurea * pcr * 100) / (purea * ucr)","unit":"%",
     "reference":"<35% prerenal","source":"Carvounis 2002"},

    {"id":"uacr","name":"Urine Albumin-to-Creatinine Ratio","abbr":"UACR","category":"Renal",
     "description":"Kidney damage marker.",
     "inputs":[{"key":"ualb","label":"Urine albumin","unit":"mg/dL"},
               {"key":"ucr","label":"Urine creatinine","unit":"mg/dL"}],
     "expression":"(ualb * 1000) / (ucr * 100)","unit":"mg/g",
     "reference":"<30 normal · 30–300 microalb · >300 macroalb","source":"NKF"},

    # ═══════════════════════════════════════════════════════
    # ENDOCRINE / HORMONAL
    # ═══════════════════════════════════════════════════════
    {"id":"fai","name":"Free Androgen Index","abbr":"FAI","category":"Endocrine",
     "description":"Free testosterone estimate.",
     "inputs":[{"key":"tt","label":"Total testosterone","unit":"nmol/L"},
               {"key":"shbg","label":"SHBG","unit":"nmol/L"}],
     "expression":"(tt * 100) / shbg","unit":"—",
     "reference":"F >5 suggests hyperandrogenism","source":"Vermeulen 1999"},

    {"id":"lh_fsh","name":"LH/FSH Ratio","abbr":"LH/FSH","category":"Endocrine",
     "description":"PCOS marker.",
     "inputs":[{"key":"lh","label":"LH","unit":"IU/L"},
               {"key":"fsh","label":"FSH","unit":"IU/L"}],
     "expression":"lh / fsh","unit":"—",
     "reference":">2 suggests PCOS","source":"—"},

    {"id":"t3_t4","name":"T3/T4 Ratio","abbr":"T3/T4","category":"Endocrine",
     "description":"Thyroid conversion marker.",
     "inputs":[{"key":"t3","label":"T3","unit":"ng/dL"},
               {"key":"t4","label":"T4","unit":"μg/dL"}],
     "expression":"(t3 * 100) / t4","unit":"—","reference":"~0.6–1.2","source":"—"},

    {"id":"ft4_ft3","name":"FT4/FT3 Ratio","abbr":"FT4/FT3","category":"Endocrine",
     "description":"Hypothyroid marker.",
     "inputs":[{"key":"ft4","label":"Free T4","unit":"pmol/L"},
               {"key":"ft3","label":"Free T3","unit":"pmol/L"}],
     "expression":"ft4 / ft3","unit":"—","reference":"~2.5–4.0","source":"—"},

    {"id":"tshi","name":"TSH Index","abbr":"TSHI","category":"Endocrine",
     "description":"Central thyroid function.",
     "inputs":[{"key":"tsh","label":"TSH","unit":"mIU/L"},
               {"key":"ft4","label":"FT4","unit":"pmol/L"}],
     "expression":"log(tsh) + 0.1345 * ft4","unit":"—",
     "reference":"—","source":"Jostel 2009"},

    {"id":"testo_estro","name":"Testosterone/Estradiol Ratio","abbr":"T/E2","category":"Endocrine",
     "description":"Androgen-estrogen balance.",
     "inputs":[{"key":"t","label":"Testosterone","unit":"ng/dL"},
               {"key":"e2","label":"Estradiol","unit":"pg/mL"}],
     "expression":"t / e2","unit":"—","reference":"—","source":"—"},

    # ═══════════════════════════════════════════════════════
    # ELECTROLYTES / ACID-BASE
    # ═══════════════════════════════════════════════════════
    {"id":"anion_gap","name":"Anion Gap","abbr":"AG","category":"Electrolytes",
     "description":"Metabolic acidosis workup.",
     "inputs":[{"key":"na","label":"Sodium","unit":"mEq/L"},
               {"key":"cl","label":"Chloride","unit":"mEq/L"},
               {"key":"hco3","label":"Bicarbonate","unit":"mEq/L"}],
     "expression":"na - (cl + hco3)","unit":"mEq/L",
     "reference":"8–12 mEq/L","source":"—"},

    {"id":"ag_corr","name":"Corrected Anion Gap","abbr":"cAG","category":"Electrolytes",
     "description":"Albumin-corrected anion gap.",
     "inputs":[{"key":"ag","label":"Anion gap","unit":"mEq/L"},
               {"key":"alb","label":"Albumin","unit":"g/dL"}],
     "expression":"ag + 2.5 * (4.0 - alb)","unit":"mEq/L","reference":"8–12","source":"Figge 1998"},

    {"id":"delta_gap","name":"Delta Gap","abbr":"ΔAG","category":"Electrolytes",
     "description":"Mixed acidosis evaluation.",
     "inputs":[{"key":"ag","label":"Anion gap","unit":"mEq/L"},
               {"key":"hco3","label":"Bicarbonate","unit":"mEq/L"}],
     "expression":"(ag - 12) + hco3 - 24","unit":"mEq/L",
     "reference":"-6 to +6 (pure)","source":"—"},

    {"id":"na_corr","name":"Corrected Sodium (Hyperglycemia)","abbr":"cNa","category":"Electrolytes",
     "description":"Sodium corrected for glucose.",
     "inputs":[{"key":"na","label":"Sodium","unit":"mEq/L"},
               {"key":"glu","label":"Glucose","unit":"mg/dL"}],
     "expression":"na + 0.024 * (glu - 100)","unit":"mEq/L","reference":"—","source":"Katz 1973"},

    {"id":"ca_corr","name":"Corrected Calcium","abbr":"cCa","category":"Electrolytes",
     "description":"Calcium corrected for albumin.",
     "inputs":[{"key":"ca","label":"Calcium","unit":"mg/dL"},
               {"key":"alb","label":"Albumin","unit":"g/dL"}],
     "expression":"ca + 0.8 * (4.0 - alb)","unit":"mg/dL",
     "reference":"8.5–10.5","source":"Payne 1973"},

    {"id":"osmo","name":"Serum Osmolality","abbr":"Osm","category":"Electrolytes",
     "description":"Calculated osmolality.",
     "inputs":[{"key":"na","label":"Sodium","unit":"mEq/L"},
               {"key":"glu","label":"Glucose","unit":"mg/dL"},
               {"key":"bun","label":"BUN","unit":"mg/dL"}],
     "expression":"2 * na + glu / 18 + bun / 2.8","unit":"mOsm/kg",
     "reference":"275–295","source":"—"},

    {"id":"winters","name":"Winter's Formula","abbr":"—","category":"Electrolytes",
     "description":"Expected PaCO2 in metabolic acidosis.",
     "inputs":[{"key":"hco3","label":"Bicarbonate","unit":"mEq/L"}],
     "expression":"1.5 * hco3 + 8","unit":"mmHg",
     "reference":"±2 expected PaCO2","source":"Winters"},

    # ═══════════════════════════════════════════════════════
    # CARDIAC / RESPIRATORY
    # ═══════════════════════════════════════════════════════
    {"id":"map","name":"Mean Arterial Pressure","abbr":"MAP","category":"Cardiac",
     "description":"Average arterial pressure.",
     "inputs":[{"key":"sbp","label":"Systolic BP","unit":"mmHg"},
               {"key":"dbp","label":"Diastolic BP","unit":"mmHg"}],
     "expression":"(sbp + 2 * dbp) / 3","unit":"mmHg",
     "reference":"70–100","source":"—"},

    {"id":"qtc_bazett","name":"QTc (Bazett)","abbr":"QTc","category":"Cardiac",
     "description":"QT corrected for HR.",
     "inputs":[{"key":"qt","label":"QT interval","unit":"ms"},
               {"key":"rr","label":"RR interval","unit":"s"}],
     "expression":"qt / sqrt(rr)","unit":"ms",
     "reference":"<450 M · <460 F","source":"Bazett 1920"},

    {"id":"qtc_fridericia","name":"QTc (Fridericia)","abbr":"QTc-F","category":"Cardiac",
     "description":"Alternative QT correction.",
     "inputs":[{"key":"qt","label":"QT interval","unit":"ms"},
               {"key":"rr","label":"RR interval","unit":"s"}],
     "expression":"qt / (rr ** (1/3))","unit":"ms","reference":"<450","source":"Fridericia 1920"},

    {"id":"rpp","name":"Rate-Pressure Product","abbr":"RPP","category":"Cardiac",
     "description":"Myocardial oxygen demand proxy.",
     "inputs":[{"key":"hr","label":"Heart rate","unit":"bpm"},
               {"key":"sbp","label":"Systolic BP","unit":"mmHg"}],
     "expression":"hr * sbp","unit":"mmHg·bpm","reference":"<20000","source":"Gobel 1978"},

    {"id":"pf_ratio","name":"PaO2/FiO2 Ratio","abbr":"P/F","category":"Respiratory",
     "description":"ARDS severity.",
     "inputs":[{"key":"pao2","label":"PaO2","unit":"mmHg"},
               {"key":"fio2","label":"FiO2 (0–1)","unit":"decimal"}],
     "expression":"pao2 / fio2","unit":"—",
     "reference":">400 normal · <300 mild ARDS","source":"ARDSNet"},

    {"id":"aa_grad","name":"Alveolar-Arterial Gradient","abbr":"A-a","category":"Respiratory",
     "description":"Oxygenation defect.",
     "inputs":[{"key":"fio2","label":"FiO2 (0–1)","unit":"decimal"},
               {"key":"paco2","label":"PaCO2","unit":"mmHg"},
               {"key":"pao2","label":"PaO2","unit":"mmHg"}],
     "expression":"fio2 * 713 - paco2 / 0.8 - pao2","unit":"mmHg",
     "reference":"<20 young","source":"—"},

    # ═══════════════════════════════════════════════════════
    # STATISTICS / RESEARCH
    # ═══════════════════════════════════════════════════════
    {"id":"cohens_d","name":"Cohen's d","abbr":"d","category":"Statistics",
     "description":"Standardised mean difference.",
     "inputs":[{"key":"m1","label":"Mean 1","unit":"—"},
               {"key":"m2","label":"Mean 2","unit":"—"},
               {"key":"s1","label":"SD 1","unit":"—"},
               {"key":"s2","label":"SD 2","unit":"—"},
               {"key":"n1","label":"n1","unit":"—"},
               {"key":"n2","label":"n2","unit":"—"}],
     "expression":"(m1 - m2) / sqrt(((n1 - 1) * s1 * s1 + (n2 - 1) * s2 * s2) / (n1 + n2 - 2))",
     "unit":"—","reference":"0.2 small · 0.5 med · 0.8 large","source":"Cohen 1988"},

    {"id":"ss_mean","name":"Sample Size for Mean","abbr":"n","category":"Statistics",
     "description":"Sample size for estimating a mean.",
     "inputs":[{"key":"sd","label":"Standard deviation","unit":"—"},
               {"key":"e","label":"Margin of error","unit":"—"}],
     "expression":"((1.96 * sd) / e) ** 2","unit":"n",
     "reference":"Round up","source":"Cochran 1977"},

    {"id":"ss_prop","name":"Sample Size for Proportion","abbr":"n","category":"Statistics",
     "description":"Sample size for estimating a proportion.",
     "inputs":[{"key":"p","label":"Expected proportion","unit":"0–1"},
               {"key":"e","label":"Margin of error","unit":"0–1"}],
     "expression":"(1.96 * 1.96 * p * (1 - p)) / (e * e)","unit":"n",
     "reference":"Round up","source":"Cochran 1977"},

    {"id":"arr","name":"Absolute Risk Reduction","abbr":"ARR","category":"Statistics",
     "description":"Difference in event rates.",
     "inputs":[{"key":"cer","label":"Control event rate","unit":"0–1"},
               {"key":"eer","label":"Experimental event rate","unit":"0–1"}],
     "expression":"cer - eer","unit":"—","reference":">0 beneficial","source":"—"},

    {"id":"nnt","name":"Number Needed to Treat","abbr":"NNT","category":"Statistics",
     "description":"Patients treated per event prevented.",
     "inputs":[{"key":"cer","label":"Control event rate","unit":"0–1"},
               {"key":"eer","label":"Experimental event rate","unit":"0–1"}],
     "expression":"1 / (cer - eer)","unit":"n","reference":"<10 strong","source":"Laupacis 1988"},

    {"id":"z_score","name":"Z-Score","abbr":"z","category":"Statistics",
     "description":"Standard score.",
     "inputs":[{"key":"x","label":"Value","unit":"—"},
               {"key":"mean","label":"Mean","unit":"—"},
               {"key":"sd","label":"SD","unit":"—"}],
     "expression":"(x - mean) / sd","unit":"—","reference":"±2 = 95%","source":"—"},
]

# ── Category order and labels ──
CATEGORIES = [
    "Anthropometric", "Metabolic", "Lipid", "Hepatic",
    "Hematology", "Renal", "Endocrine", "Electrolytes",
    "Cardiac", "Respiratory", "Statistics",
]

def list_categories():
    return CATEGORIES

def find(fid):
    for f in LIBRARY:
        if f["id"] == fid:
            return f
    return None

def search(q):
    q = (q or "").strip().lower()
    if not q:
        return LIBRARY
    return [f for f in LIBRARY
            if q in f["name"].lower()
            or q in f.get("abbr", "").lower()
            or q in f.get("category", "").lower()
            or q in f.get("description", "").lower()]

def by_category(cat=None):
    if not cat:
        return LIBRARY
    return [f for f in LIBRARY if f["category"] == cat]
