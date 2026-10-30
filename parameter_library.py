"""World-standard medical parameter catalog (~180 entries).
Compact tuple format: (code, name, category, subcategory, data_type, unit,
                       ref_low, ref_high, ref_text, choices, tags)"""

CATALOG = [
    # ─── Demographic ─────────────────────────────────────
    ("AGE","Age","Demographic","Basic","Decimal","years",None,None,"","",["basic","common"]),
    ("SEX","Sex","Demographic","Basic","Choice","",None,None,"","Male,Female,Other",["basic","common"]),
    ("EDU","Education level","Demographic","Socioeconomic","Choice","",None,None,"","None,Primary,Secondary,Graduate,Postgraduate",["socio"]),
    ("OCC","Occupation","Demographic","Socioeconomic","Text","",None,None,"","",["socio"]),
    ("MARITAL","Marital status","Demographic","Socioeconomic","Choice","",None,None,"","Single,Married,Divorced,Widowed",["socio"]),
    ("RESIDENCE","Residence","Demographic","Socioeconomic","Choice","",None,None,"","Urban,Rural,Semi-urban",["socio"]),
    ("INCOME","Monthly income","Demographic","Socioeconomic","Decimal","currency",None,None,"","",["socio"]),
    ("ETHNICITY","Ethnicity","Demographic","Socioeconomic","Text","",None,None,"","",["socio"]),
    ("SMOKING","Smoking status","Demographic","Lifestyle","Choice","",None,None,"","Never,Current,Former",["lifestyle"]),
    ("SMOKE_PK","Pack-years","Demographic","Lifestyle","Decimal","pack-years",None,None,"","",["lifestyle"]),
    ("ALCOHOL","Alcohol use","Demographic","Lifestyle","Choice","",None,None,"","Never,Occasional,Regular",["lifestyle"]),
    ("PHYS_ACT","Physical activity","Demographic","Lifestyle","Choice","",None,None,"","Sedentary,Moderate,Active",["lifestyle"]),

    # ─── Anthropometric ──────────────────────────────────
    ("HEIGHT","Height","Anthropometric","Basic","Decimal","cm",None,None,"","",["basic","common"]),
    ("WEIGHT","Weight","Anthropometric","Basic","Decimal","kg",None,None,"","",["basic","common"]),
    ("BMI","Body mass index","Anthropometric","Index","Decimal","kg/m²",18.5,24.9,"18.5–24.9 normal","",["basic","common"]),
    ("WAIST","Waist circumference","Anthropometric","Girth","Decimal","cm",None,None,"","",["basic"]),
    ("HIP","Hip circumference","Anthropometric","Girth","Decimal","cm",None,None,"","",["basic"]),
    ("WHR","Waist-to-hip ratio","Anthropometric","Index","Decimal","ratio",None,None,"M<0.9 F<0.85","",["basic"]),
    ("WHTR","Waist-to-height ratio","Anthropometric","Index","Decimal","ratio",None,0.5,"<0.5 desirable","",["basic"]),
    ("NECK","Neck circumference","Anthropometric","Girth","Decimal","cm",None,None,"","",["basic"]),
    ("MUAC","Mid-upper arm circumference","Anthropometric","Girth","Decimal","cm",None,None,"","",["basic"]),
    ("BSA","Body surface area","Anthropometric","Index","Decimal","m²",1.6,2.0,"1.6–2.0","",["basic"]),

    # ─── Vital signs ─────────────────────────────────────
    ("BP_SYS","Blood pressure — systolic","Vitals","BP","Decimal","mmHg",90,120,"90–120","",["vitals"]),
    ("BP_DIA","Blood pressure — diastolic","Vitals","BP","Decimal","mmHg",60,80,"60–80","",["vitals"]),
    ("PULSE","Pulse rate","Vitals","Basic","Decimal","bpm",60,100,"60–100","",["vitals"]),
    ("TEMP","Body temperature","Vitals","Basic","Decimal","°C",36.1,37.2,"36.1–37.2","",["vitals"]),
    ("RR","Respiratory rate","Vitals","Basic","Decimal","/min",12,20,"12–20","",["vitals"]),
    ("SPO2","SpO₂","Vitals","Basic","Decimal","%",95,100,"≥95","",["vitals"]),

    # ─── CBC / Hematology ────────────────────────────────
    ("HB","Hemoglobin","Hematology","CBC","Decimal","g/dL",12,16,"M 13–17, F 12–15","",["cbc","common"]),
    ("RBC","RBC count","Hematology","CBC","Decimal","10⁶/μL",4.2,5.9,"4.2–5.9","",["cbc"]),
    ("WBC","WBC count","Hematology","CBC","Decimal","10³/μL",4,11,"4–11","",["cbc","common"]),
    ("PLT","Platelet count","Hematology","CBC","Decimal","10³/μL",150,450,"150–450","",["cbc","common"]),
    ("HCT","Hematocrit","Hematology","CBC","Decimal","%",36,50,"36–50","",["cbc"]),
    ("MCV","MCV","Hematology","Indices","Decimal","fL",80,100,"80–100","",["cbc"]),
    ("MCH","MCH","Hematology","Indices","Decimal","pg",27,33,"27–33","",["cbc"]),
    ("MCHC","MCHC","Hematology","Indices","Decimal","g/dL",32,36,"32–36","",["cbc"]),
    ("RDW","RDW","Hematology","Indices","Decimal","%",11.5,14.5,"11.5–14.5","",["cbc"]),
    ("NEUT","Neutrophils","Hematology","Differential","Decimal","%",40,75,"40–75","",["cbc","diff"]),
    ("LYMPH","Lymphocytes","Hematology","Differential","Decimal","%",20,45,"20–45","",["cbc","diff"]),
    ("MONO","Monocytes","Hematology","Differential","Decimal","%",2,10,"2–10","",["cbc","diff"]),
    ("EOS","Eosinophils","Hematology","Differential","Decimal","%",1,6,"1–6","",["cbc","diff"]),
    ("BASO","Basophils","Hematology","Differential","Decimal","%",0,1,"0–1","",["cbc","diff"]),
    ("ESR","ESR","Hematology","Inflammation","Decimal","mm/hr",None,20,"<20","",["inflam"]),
    ("RETIC","Reticulocyte count","Hematology","CBC","Decimal","%",0.5,2.5,"0.5–2.5","",["cbc"]),

    # ─── Coagulation ─────────────────────────────────────
    ("PT","Prothrombin time","Coagulation","Basic","Decimal","s",11,13.5,"11–13.5","",["coag"]),
    ("INR","INR","Coagulation","Basic","Decimal","ratio",0.8,1.2,"0.8–1.2","",["coag"]),
    ("APTT","aPTT","Coagulation","Basic","Decimal","s",25,35,"25–35","",["coag"]),
    ("FIBRIN","Fibrinogen","Coagulation","Basic","Decimal","mg/dL",200,400,"200–400","",["coag","inflam"]),
    ("DDIMER","D-dimer","Coagulation","Basic","Decimal","ng/mL",None,500,"<500","",["coag"]),
    ("BT","Bleeding time","Coagulation","Basic","Decimal","min",2,7,"2–7","",["coag"]),

    # ─── Liver function ──────────────────────────────────
    ("ALT","ALT (SGPT)","Biochemistry","Liver","Decimal","U/L",7,35,"7–35","",["liver","common"]),
    ("AST","AST (SGOT)","Biochemistry","Liver","Decimal","U/L",10,40,"10–40","",["liver","common"]),
    ("ALP","Alkaline phosphatase","Biochemistry","Liver","Decimal","U/L",44,147,"44–147","",["liver"]),
    ("GGT","GGT","Biochemistry","Liver","Decimal","U/L",9,48,"9–48","",["liver"]),
    ("TBIL","Total bilirubin","Biochemistry","Liver","Decimal","mg/dL",0.1,1.2,"0.1–1.2","",["liver"]),
    ("DBIL","Direct bilirubin","Biochemistry","Liver","Decimal","mg/dL",0,0.3,"0–0.3","",["liver"]),
    ("IBIL","Indirect bilirubin","Biochemistry","Liver","Decimal","mg/dL",0.1,0.9,"0.1–0.9","",["liver"]),
    ("TP","Total protein","Biochemistry","Liver","Decimal","g/dL",6,8.3,"6–8.3","",["liver"]),
    ("ALB","Albumin","Biochemistry","Liver","Decimal","g/dL",3.5,5.5,"3.5–5.5","",["liver"]),
    ("GLOB","Globulin","Biochemistry","Liver","Decimal","g/dL",2,3.5,"2–3.5","",["liver"]),
    ("AG_RATIO","Albumin/globulin ratio","Biochemistry","Liver","Decimal","ratio",1.1,2.5,"1.1–2.5","",["liver"]),

    # ─── Renal function ──────────────────────────────────
    ("UREA","Blood urea","Biochemistry","Renal","Decimal","mg/dL",15,45,"15–45","",["renal"]),
    ("BUN","Blood urea nitrogen","Biochemistry","Renal","Decimal","mg/dL",7,20,"7–20","",["renal"]),
    ("CREAT","Serum creatinine","Biochemistry","Renal","Decimal","mg/dL",0.6,1.3,"0.6–1.3","",["renal","common"]),
    ("UA","Uric acid","Biochemistry","Renal","Decimal","mg/dL",2.4,6.0,"M 3.4–7.0, F 2.4–6.0","",["renal"]),
    ("EGFR","eGFR","Biochemistry","Renal","Decimal","mL/min/1.73m²",90,None,"≥90","",["renal"]),
    ("CYSC","Cystatin C","Biochemistry","Renal","Decimal","mg/L",0.5,1.0,"0.5–1.0","",["renal"]),
    ("UACR","Urine albumin/creatinine","Biochemistry","Renal","Decimal","mg/g",None,30,"<30","",["renal"]),

    # ─── Electrolytes ────────────────────────────────────
    ("NA","Sodium","Electrolytes","Basic","Decimal","mEq/L",135,145,"135–145","",["elec"]),
    ("K","Potassium","Electrolytes","Basic","Decimal","mEq/L",3.5,5.1,"3.5–5.1","",["elec"]),
    ("CL","Chloride","Electrolytes","Basic","Decimal","mEq/L",98,107,"98–107","",["elec"]),
    ("HCO3","Bicarbonate","Electrolytes","Basic","Decimal","mEq/L",22,29,"22–29","",["elec"]),
    ("CA","Calcium","Electrolytes","Basic","Decimal","mg/dL",8.5,10.5,"8.5–10.5","",["elec"]),
    ("PHOS","Phosphate","Electrolytes","Basic","Decimal","mg/dL",2.5,4.5,"2.5–4.5","",["elec"]),
    ("MG","Magnesium","Electrolytes","Basic","Decimal","mg/dL",1.7,2.2,"1.7–2.2","",["elec"]),

    # ─── Lipid profile ───────────────────────────────────
    ("TC","Total cholesterol","Biochemistry","Lipid","Decimal","mg/dL",None,200,"<200","",["lipid","common"]),
    ("HDL","HDL cholesterol","Biochemistry","Lipid","Decimal","mg/dL",40,None,"M>40, F>50","",["lipid","common"]),
    ("LDL","LDL cholesterol","Biochemistry","Lipid","Decimal","mg/dL",None,100,"<100 optimal","",["lipid","common"]),
    ("VLDL","VLDL cholesterol","Biochemistry","Lipid","Decimal","mg/dL",5,40,"5–40","",["lipid"]),
    ("TG","Triglycerides","Biochemistry","Lipid","Decimal","mg/dL",None,150,"<150","",["lipid","common"]),
    ("NONHDL","Non-HDL cholesterol","Biochemistry","Lipid","Decimal","mg/dL",None,130,"<130","",["lipid"]),
    ("APOA1","Apolipoprotein A1","Biochemistry","Lipid","Decimal","mg/dL",110,180,"110–180","",["lipid"]),
    ("APOB","Apolipoprotein B","Biochemistry","Lipid","Decimal","mg/dL",55,125,"55–125","",["lipid"]),
    ("LPA","Lipoprotein(a)","Biochemistry","Lipid","Decimal","mg/dL",None,30,"<30","",["lipid"]),

    # ─── Glucose metabolism ──────────────────────────────
    ("FBS","Fasting blood sugar","Biochemistry","Glucose","Decimal","mg/dL",70,100,"70–100","",["glucose","common"]),
    ("PPBS","Post-prandial blood sugar","Biochemistry","Glucose","Decimal","mg/dL",None,140,"<140","",["glucose"]),
    ("RBS","Random blood sugar","Biochemistry","Glucose","Decimal","mg/dL",70,140,"70–140","",["glucose"]),
    ("HBA1C","HbA1c","Biochemistry","Glucose","Decimal","%",None,5.7,"<5.7 normal · 5.7–6.4 prediabetes · ≥6.5 diabetes","",["glucose","common"]),
    ("FINS","Fasting insulin","Biochemistry","Glucose","Decimal","μU/mL",2,25,"2–25","",["glucose"]),
    ("CPEP","C-peptide","Biochemistry","Glucose","Decimal","ng/mL",0.8,3.9,"0.8–3.9","",["glucose"]),
    ("HOMA_IR","HOMA-IR","Biochemistry","Glucose","Decimal","—",None,2.0,"<2.0","",["glucose","computed"]),
    ("HOMA_B","HOMA-β","Biochemistry","Glucose","Decimal","%",None,None,"~100%","",["glucose","computed"]),
    ("QUICKI","QUICKI","Biochemistry","Glucose","Decimal","—",0.45,None,">0.45","",["glucose","computed"]),

    # ─── Thyroid ─────────────────────────────────────────
    ("TSH","TSH","Endocrine","Thyroid","Decimal","mIU/L",0.4,4.0,"0.4–4.0","",["thyroid"]),
    ("T3","Total T3","Endocrine","Thyroid","Decimal","ng/dL",80,200,"80–200","",["thyroid"]),
    ("T4","Total T4","Endocrine","Thyroid","Decimal","μg/dL",5.0,12.0,"5.0–12.0","",["thyroid"]),
    ("FT3","Free T3","Endocrine","Thyroid","Decimal","pg/mL",2.3,4.2,"2.3–4.2","",["thyroid"]),
    ("FT4","Free T4","Endocrine","Thyroid","Decimal","ng/dL",0.8,1.8,"0.8–1.8","",["thyroid"]),
    ("ATPO","Anti-TPO antibody","Endocrine","Thyroid","Decimal","IU/mL",None,35,"<35","",["thyroid","autoimmune"]),
    ("ATG","Anti-thyroglobulin","Endocrine","Thyroid","Decimal","IU/mL",None,40,"<40","",["thyroid","autoimmune"]),

    # ─── Reproductive hormones ───────────────────────────
    ("FSH","FSH","Endocrine","Reproductive","Decimal","IU/L",3,12,"cycle-dependent","",["repro"]),
    ("LH","LH","Endocrine","Reproductive","Decimal","IU/L",2,12,"cycle-dependent","",["repro"]),
    ("PRL","Prolactin","Endocrine","Reproductive","Decimal","ng/mL",4,23,"F 4–23, M 3–15","",["repro"]),
    ("E2","Estradiol","Endocrine","Reproductive","Decimal","pg/mL",19,530,"cycle-dependent","",["repro"]),
    ("PROG","Progesterone","Endocrine","Reproductive","Decimal","ng/mL",0.1,25,"cycle-dependent","",["repro"]),
    ("TT","Total testosterone","Endocrine","Reproductive","Decimal","ng/dL",8,60,"F 8–60, M 300–1000","",["repro"]),
    ("FT","Free testosterone","Endocrine","Reproductive","Decimal","pg/mL",0.3,3.2,"F 0.3–3.2","",["repro"]),
    ("SHBG","SHBG","Endocrine","Reproductive","Decimal","nmol/L",18,144,"18–144","",["repro"]),
    ("DHEAS","DHEA-S","Endocrine","Reproductive","Decimal","μg/dL",35,430,"age-dependent","",["repro"]),
    ("AMH","AMH","Endocrine","Reproductive","Decimal","ng/mL",1,4,"1–4 normal","",["repro","pcos"]),
    ("A4","Androstenedione","Endocrine","Reproductive","Decimal","ng/dL",30,200,"30–200","",["repro"]),
    ("17OHP","17-OH progesterone","Endocrine","Reproductive","Decimal","ng/mL",0.1,2.0,"0.1–2.0","",["repro"]),

    # ─── PCOS-specific ───────────────────────────────────
    ("FG_SCORE","Ferriman-Gallwey score","Clinical","PCOS","Decimal","score",None,8,"<8","",["pcos"]),
    ("OV_VOL","Ovarian volume","Clinical","PCOS","Decimal","mL",None,10,"<10","",["pcos"]),
    ("AFC","Antral follicle count","Clinical","PCOS","Integer","count",None,12,"<12","",["pcos"]),
    ("MENARCHE","Age at menarche","Clinical","PCOS","Decimal","years",11,15,"11–15","",["pcos"]),
    ("CYCLE","Menstrual cycle length","Clinical","PCOS","Decimal","days",21,35,"21–35","",["pcos"]),
    ("ACNE","Acne","Clinical","PCOS","Choice","",None,None,"","None,Mild,Moderate,Severe",["pcos"]),
    ("ALOPECIA","Androgenic alopecia","Clinical","PCOS","Yes/No","",None,None,"","",["pcos"]),

    # ─── Inflammatory markers ────────────────────────────
    ("CRP","CRP","Biochemistry","Inflammation","Decimal","mg/L",None,5,"<5","",["inflam"]),
    ("HSCRP","hs-CRP","Biochemistry","Inflammation","Decimal","mg/L",None,1,"<1 low risk","",["inflam","cardiac"]),
    ("FERRITIN","Ferritin","Biochemistry","Inflammation","Decimal","ng/mL",15,150,"15–150","",["inflam","iron"]),
    ("PCT","Procalcitonin","Biochemistry","Inflammation","Decimal","ng/mL",None,0.05,"<0.05","",["inflam"]),
    ("IL6","Interleukin-6","Biochemistry","Inflammation","Decimal","pg/mL",None,7,"<7","",["inflam"]),
    ("TNFA","TNF-α","Biochemistry","Inflammation","Decimal","pg/mL",None,8.1,"<8.1","",["inflam"]),

    # ─── Cardiac markers ─────────────────────────────────
    ("TROP_I","Troponin I","Biochemistry","Cardiac","Decimal","ng/mL",None,0.04,"<0.04","",["cardiac"]),
    ("TROP_T","Troponin T","Biochemistry","Cardiac","Decimal","ng/mL",None,0.01,"<0.01","",["cardiac"]),
    ("CKMB","CK-MB","Biochemistry","Cardiac","Decimal","ng/mL",None,6.3,"<6.3","",["cardiac"]),
    ("BNP","BNP","Biochemistry","Cardiac","Decimal","pg/mL",None,100,"<100","",["cardiac"]),
    ("NT_BNP","NT-proBNP","Biochemistry","Cardiac","Decimal","pg/mL",None,125,"<125","",["cardiac"]),
    ("HCY","Homocysteine","Biochemistry","Cardiac","Decimal","μmol/L",5,15,"5–15","",["cardiac"]),

    # ─── Iron studies / vitamins ─────────────────────────
    ("IRON","Serum iron","Biochemistry","Iron","Decimal","μg/dL",60,170,"60–170","",["iron"]),
    ("TIBC","TIBC","Biochemistry","Iron","Decimal","μg/dL",240,450,"240–450","",["iron"]),
    ("TSAT","Transferrin saturation","Biochemistry","Iron","Decimal","%",20,50,"20–50","",["iron"]),
    ("VITD","Vitamin D (25-OH)","Biochemistry","Vitamins","Decimal","ng/mL",30,100,"30–100","",["vitamin"]),
    ("VITB12","Vitamin B12","Biochemistry","Vitamins","Decimal","pg/mL",200,900,"200–900","",["vitamin"]),
    ("FOLATE","Folate","Biochemistry","Vitamins","Decimal","ng/mL",3,17,"3–17","",["vitamin"]),
    ("ZINC","Zinc","Biochemistry","Vitamins","Decimal","μg/dL",60,120,"60–120","",["mineral"]),
    ("COPPER","Copper","Biochemistry","Vitamins","Decimal","μg/dL",70,140,"70–140","",["mineral"]),

    # ─── Oxidative stress / Research ─────────────────────
    ("MDA","Malondialdehyde","Research","Oxidative","Decimal","nmol/mL",None,1.5,"<1.5","",["oxstress","research"]),
    ("SOD","Superoxide dismutase","Research","Oxidative","Decimal","U/mL",None,None,"—","",["oxstress","research"]),
    ("CAT","Catalase","Research","Oxidative","Decimal","U/mL",None,None,"—","",["oxstress","research"]),
    ("GSH","Reduced glutathione","Research","Oxidative","Decimal","μmol/L",None,None,"—","",["oxstress","research"]),
    ("GPX","Glutathione peroxidase","Research","Oxidative","Decimal","U/L",None,None,"—","",["oxstress","research"]),
    ("TAC","Total antioxidant capacity","Research","Oxidative","Decimal","mmol/L",None,None,"—","",["oxstress","research"]),
    ("TOS","Total oxidant status","Research","Oxidative","Decimal","μmol/L",None,None,"—","",["oxstress","research"]),
    ("8OHDG","8-OHdG","Research","Oxidative","Decimal","ng/mL",None,None,"—","",["oxstress","research"]),

    # ─── Tumor markers ───────────────────────────────────
    ("AFP","AFP","Biochemistry","Tumor","Decimal","ng/mL",None,10,"<10","",["tumor"]),
    ("CEA","CEA","Biochemistry","Tumor","Decimal","ng/mL",None,5,"<5","",["tumor"]),
    ("CA125","CA-125","Biochemistry","Tumor","Decimal","U/mL",None,35,"<35","",["tumor"]),
    ("CA199","CA 19-9","Biochemistry","Tumor","Decimal","U/mL",None,37,"<37","",["tumor"]),
    ("CA153","CA 15-3","Biochemistry","Tumor","Decimal","U/mL",None,30,"<30","",["tumor"]),
    ("PSA","PSA","Biochemistry","Tumor","Decimal","ng/mL",None,4,"<4","",["tumor"]),

    # ─── Urine analysis ──────────────────────────────────
    ("U_PH","Urine pH","Urine","Physical","Decimal","pH",4.5,8.0,"4.5–8.0","",["urine"]),
    ("U_SG","Urine specific gravity","Urine","Physical","Decimal","—",1.005,1.030,"1.005–1.030","",["urine"]),
    ("U_PROT","Urine protein","Urine","Chemical","Choice","",None,None,"","Negative,Trace,1+,2+,3+,4+",["urine"]),
    ("U_GLU","Urine glucose","Urine","Chemical","Choice","",None,None,"","Negative,Trace,1+,2+,3+,4+",["urine"]),
    ("U_KET","Urine ketones","Urine","Chemical","Choice","",None,None,"","Negative,Trace,Small,Moderate,Large",["urine"]),
    ("U_BLOOD","Urine blood","Urine","Chemical","Choice","",None,None,"","Negative,Trace,Small,Moderate,Large",["urine"]),
    ("U_LE","Urine leukocytes","Urine","Chemical","Choice","",None,None,"","Negative,Trace,1+,2+,3+",["urine"]),
    ("U_NIT","Urine nitrites","Urine","Chemical","Yes/No","",None,None,"","",["urine"]),
    ("U_RBC","Urine RBC (microscopy)","Urine","Microscopy","Decimal","/hpf",None,2,"0–2","",["urine"]),
    ("U_WBC","Urine WBC (microscopy)","Urine","Microscopy","Decimal","/hpf",None,5,"0–5","",["urine"]),

    # ─── Coagulation extras ──────────────────────────────
    ("ANTITHROMBIN","Antithrombin III","Coagulation","Special","Decimal","%",80,120,"80–120","",["coag"]),
    ("PROT_C","Protein C","Coagulation","Special","Decimal","%",70,140,"70–140","",["coag"]),
    ("PROT_S","Protein S","Coagulation","Special","Decimal","%",60,140,"60–140","",["coag"]),

    # ─── Clinical scores / outcomes ──────────────────────
    ("NIHSS","NIH Stroke Scale","Clinical","Score","Integer","score",0,42,"0 no deficit","",["score"]),
    ("GCS","Glasgow Coma Scale","Clinical","Score","Integer","score",3,15,"15 normal","",["score"]),
    ("MMSE","MMSE","Clinical","Score","Integer","score",24,30,"≥24 normal","",["score"]),
    ("VAS","Visual Analog Scale","Clinical","Score","Integer","score",0,10,"0 none, 10 worst","",["score"]),
    ("KARNOF","Karnofsky Performance Score","Clinical","Score","Integer","%",0,100,"100 normal","",["score"]),

    # ─── Body composition / Advanced ─────────────────────
    ("BODY_FAT","Body fat %","Anthropometric","Composition","Decimal","%",None,None,"—","",["comp"]),
    ("MUSCLE","Skeletal muscle mass","Anthropometric","Composition","Decimal","kg",None,None,"—","",["comp"]),
    ("VISC_FAT","Visceral fat","Anthropometric","Composition","Decimal","level",1,12,"1–12","",["comp"]),
    ("BMR","Basal metabolic rate","Anthropometric","Composition","Decimal","kcal",None,None,"—","",["comp"]),

    # ─── Study metadata ──────────────────────────────────
    ("VISIT","Visit","Study","Logistics","Text","",None,None,"","",["study"]),
    ("GROUP","Group","Study","Logistics","Choice","",None,None,"","Control,Case",["study"]),
    ("SUBJ_ID","Subject ID","Study","Logistics","Text","",None,None,"","",["study"]),
    ("CONSENT","Consent","Study","Logistics","Long text","",None,None,"","",["study"]),
    ("COMPLIANCE","Compliance","Study","Logistics","Choice","",None,None,"","Good,Fair,Poor",["study"]),
]

# ─── Expand to dicts ───
def _expand(row):
    code, name, cat, sub, dt, unit, lo, hi, rt, ch, tags = row
    return {
        "id": code.lower(), "code": code, "name": name,
        "category": cat, "subcategory": sub,
        "data_type": dt, "unit": unit,
        "ref_low": lo, "ref_high": hi, "ref_text": rt,
        "choices": ch, "tags": tags,
    }

LIBRARY = [_expand(r) for r in CATALOG]

CATEGORIES = ["Demographic","Anthropometric","Vitals","Hematology","Coagulation",
              "Biochemistry","Electrolytes","Endocrine","Clinical","Research",
              "Urine","Study"]

def all_params(): return LIBRARY
def total(): return len(LIBRARY)

def find(pid):
    for p in LIBRARY:
        if p["id"] == pid: return p
    return None

def search(q):
    q = (q or "").strip().lower()
    if not q: return LIBRARY
    return [p for p in LIBRARY
            if q in p["name"].lower()
            or q in p["code"].lower()
            or q in p["category"].lower()
            or q in p["subcategory"].lower()
            or any(q in t for t in p["tags"])]

def by_category(cat=None):
    if not cat: return LIBRARY
    return [p for p in LIBRARY if p["category"] == cat]

def by_tag(tag):
    return [p for p in LIBRARY if tag in p["tags"]]

def categories_of(p):
    return {p["category"]}
