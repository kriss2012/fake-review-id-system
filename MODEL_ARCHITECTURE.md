# VERIVIEW AI // Fraud Detection Model Architecture & Inner Workings

This document provides a publication-grade breakdown of the mathematical foundations, machine learning pipeline, feature engineering, and deception attribution heuristics powering the **VeriView AI Fake Review Detection Engine**.

---

## 1. System Overview & Objective

The primary objective of the VeriView AI engine is to evaluate customer product and service reviews across three modalities (raw text, file uploads, and screenshot images via Pytesseract OCR), detect deception and synthetic bot patterns, and produce a calibrated deception threat index with token-level explainability.

```
+--------------------------------------------------------------------------------------------------------+
|                                VERIVIEW AI FRAUD RADAR INFERENCE PIPELINE                              |
+--------------------------------------------------------------------------------------------------------+
|                                                                                                        |
|  [ Multimodal Ingest: Direct Text | Plaintext .txt | Screenshot Image via Pytesseract OCR ]            |
|          |                                                                                             |
|          v                                                                                             |
|  [ Stage 1: Regex Lexical Sanitization & Normalization ] --> Strip non-letters, lowercase              |
|          |                                                                                             |
|          v                                                                                             |
|  [ Stage 2: Martin Porter 1980 Stemmer & NLTK Stopword Pruning ] --> Reduce inflections to roots       |
|          |                                                                                             |
|          v                                                                                             |
|  [ Stage 3: Sublinear TF-IDF Feature Projection (84-D) ] --> Sparse vectorization                      |
|          |                                                                                             |
|          v                                                                                             |
|  [ Stage 4: Regularized Logistic Regression Sigmoid Hyperplane ] --> L2 Ridge penalty                  |
|          |                                                                                             |
|          v                                                                                             |
|  [ Stage 5: Sigmoid Probability Calibration & Local Linear Attribution ] --> Fraud vs Authentic       |
|                                                                                                        |
+--------------------------------------------------------------------------------------------------------+
```

---

## 2. Dataset Anatomy

The training corpus (`fake_review_dataset.csv`) contains **2,000 verified customer reviews** with a pristine 50/50 balance:

| Label Category | Sample Count | Ratio | Key Linguistic Traits |
|---|---|---|---|
| **Class 1: Computer Generated / Fake** | 1,000 | 50.0% | Extreme superlatives ("best ever", "overnight miracle", "total scam"), low nuanced detail, hyperbolic polarity |
| **Class 0: Original / Authentic** | 1,000 | 50.0% | Balanced sentiment, qualified observations ("decent", "performs well so far", "pleased", "arrived on time") |

---

## 3. Mathematical Foundations

### 3.1 Martin Porter Stemming & Normalization
Natural language features are mapped to their morphological stems using Martin Porter's 1980 suffix stripping algorithm. For example:
- `arrived` &rarr; `arriv`
- `satisfaction` &rarr; `satisfi`
- `miracles` &rarr; `miracl`
- `completely` &rarr; `complet`

### 3.2 Term Frequency - Inverse Document Frequency (TF-IDF)
For term $t$ in review $d$ across corpus $D$:

$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \left( \ln\frac{1 + |D|}{1 + \text{DF}(t, D)} + 1 \right)$$

With sublinear term frequency scaling applied:

$$\text{TF}_{\text{sublinear}}(t, d) = 1 + \ln(\text{TF}(t, d)) \quad \forall \; \text{TF}(t, d) > 0$$

### 3.3 Logistic Sigmoid Classification
A single separating hyperplane computes the logit:

$$z = \mathbf{w}^T \mathbf{x} + b$$

Where $\mathbf{w} \in \mathbb{R}^{84}$ represents the feature weights, $\mathbf{x}$ is the TF-IDF representation of the review, and $b$ is the scalar intercept.

The probability of fraud is evaluated using the standard logistic sigmoid function:

$$P(\text{Fake} \mid \mathbf{x}) = \sigma(z) = \frac{1}{1 + e^{-z}} = \frac{1}{1 + e^{-(\mathbf{w}^T \mathbf{x} + b)}}$$

And the authentic probability is complementary:

$$P(\text{Original} \mid \mathbf{x}) = 1 - P(\text{Fake} \mid \mathbf{x})$$

### 3.4 Regularization & Objective Loss Function
The model parameters $\mathbf{w}$ and $b$ are trained by minimizing the L2-regularized binary cross-entropy loss (Log-Loss):

$$\mathcal{L}(\mathbf{w}, b) = -\frac{1}{N} \sum_{i=1}^N \left[ y_i \ln(\hat{y}_i) + (1 - y_i) \ln(1 - \hat{y}_i) \right] + \frac{1}{2C} \|\mathbf{w}\|_2^2$$

With regularization parameter $C = 1.0$.

---

## 4. Local Feature Attribution (Explainability)

Rather than outputting an opaque label, VeriView AI evaluates the linear logit contribution of each word stem:

$$\text{Attribution}(t_j) = w_j \times x_j$$

- **Positive Attribution ($w_j > 0$)**: Stems that actively pushed the logit towards fraudulent classification (e.g., `ever` $+2.701$, `avoid` $+2.694$, `fake` $+2.648$, `best` $+2.554$, `miracl` $+1.721$).
- **Negative Attribution ($w_j < 0$)**: Stems that actively pulled the logit towards authentic classification (e.g., `decent` $-3.661$, `well` $-3.568$, `perform` $-3.397$, `pleas` $-2.786$, `overal` $-2.758$).

---

## 5. Deception Threat Tiers

| Threat Tier | Probability Range | Verdict Description |
|---|---|---|
| **CRITICAL_FRAUD** | $P(\text{Fake}) \ge 80\%$ | Confirmed synthetic or bot-generated review exhibiting acute hyperbolic markers. |
| **SUSPICIOUS_ANOMALY** | $50\% \le P(\text{Fake}) < 80\%$ | Probable promotional review or bot-incentivized feedback. |
| **BALANCED_NUANCED** | $25\% \le P(\text{Fake}) < 50\%$ | Likely authentic review with minor promotional phrasing. |
| **AUTHENTIC_VERIFIED** | $P(\text{Fake}) < 25\%$ | Verified genuine human experience detailing realistic functional observations. |

