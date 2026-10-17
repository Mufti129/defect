#!/usr/bin/env python3
import os
import sys
import time
import json
from pathlib import Path
import numpy as np

sys.path.insert(0, os.path.abspath('streamlit_inspection_app'))
from evaluate_benchmark_v5 import collect_test_units_per_grade, GRADES, GRADE_TO_ID
from defect_detector import DefectDetector
from ml_grading_aggregator import MLGradingAggregator
from grading_engine import GradingEngine

def run_eval_for_model(version: str, weights_path: str, ml_path: str = 'weights/ml_grading_model_v3.joblib'):
    print(f'\n==========================================')
    print(f'RUNNING REAL EVALUATION FOR: {version.upper()}')
    print(f'Weights: {weights_path}')
    print(f'==========================================')
    
    units = collect_test_units_per_grade(units_per_grade=25)
    print(f'Collected {len(units)} units (25 A, 25 B, 25 C, 25 D)')

    detector = DefectDetector(weights_path=weights_path, device='cpu')
    aggregator = MLGradingAggregator(model_path=ml_path)
    engine = GradingEngine(detector=detector, ml_aggregator=aggregator)

    cm = np.zeros((4, 4), dtype=int)
    latencies = []
    unit_results = []

    t_start = time.time()
    for i, (u_id, true_g, views) in enumerate(units):
        t0 = time.time()
        rep = engine.evaluate_phone_unit(u_id, views, version=version)
        dt = time.time() - t0
        latencies.append(dt)

        pred_g = rep.get('final_grade', 'D')
        t_idx = GRADE_TO_ID[true_g]
        p_idx = GRADE_TO_ID[pred_g]
        cm[t_idx, p_idx] += 1

        unit_results.append({
            'unit_id': u_id,
            'true_grade': true_g,
            'pred_grade': pred_g,
            'latency': round(dt, 3),
            'is_correct': bool(true_g == pred_g)
        })

        if (i + 1) % 25 == 0:
            print(f'[{version.upper()}] Processed {i+1}/100 units | Avg Latency: {np.mean(latencies):.2f}s | Acc so far: {np.trace(cm)/(i+1)*100:.1f}%')

    total_time = time.time() - t_start
    total_correct = int(np.trace(cm))
    acc = total_correct / len(units)

    # Per grade metrics
    per_grade = {}
    f1_list = []
    prec_list = []
    rec_list = []
    
    over_grading = int(np.sum([cm[r, c] for r in range(4) for c in range(4) if c < r]))
    under_grading = int(np.sum([cm[r, c] for r in range(4) for c in range(4) if c > r]))
    crit_inv_d_to_a = int(cm[3, 0])

    for g in GRADES:
        idx = GRADE_TO_ID[g]
        tp = int(cm[idx, idx])
        fp = int(np.sum(cm[:, idx]) - tp)
        fn = int(np.sum(cm[idx, :]) - tp)
        support = int(np.sum(cm[idx, :]))

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        f1_list.append(f1)
        prec_list.append(prec)
        rec_list.append(rec)

        per_grade[g] = {
            'support': support,
            'tp': tp,
            'fp': fp,
            'fn': fn,
            'precision': round(prec * 100, 2),
            'recall': round(rec * 100, 2),
            'f1_score': round(f1, 4)
        }

    macro_avg = {
        'support': len(units),
        'tp': total_correct,
        'fp': int(len(units) - total_correct),
        'fn': int(len(units) - total_correct),
        'precision': round(float(np.mean(prec_list)) * 100, 2),
        'recall': round(float(np.mean(rec_list)) * 100, 2),
        'f1_score': round(float(np.mean(f1_list)), 4)
    }

    res_summary = {
        'version': version,
        'weights': weights_path,
        'total_units': len(units),
        'accuracy_pct': round(acc * 100, 2),
        'macro_f1': round(float(np.mean(f1_list)), 4),
        'confusion_matrix': cm.tolist(),
        'per_grade': per_grade,
        'macro_avg': macro_avg,
        'over_grading_count': over_grading,
        'over_grading_pct': round(over_grading / len(units) * 100, 2),
        'under_grading_count': under_grading,
        'under_grading_pct': round(under_grading / len(units) * 100, 2),
        'critical_inversions': crit_inv_d_to_a,
        'total_time_sec': round(total_time, 2),
        'avg_latency_sec': round(float(np.mean(latencies)), 3)
    }

    out_file = f'reports/real_benchmark_{version}.json'
    with open(out_file, 'w') as f:
        json.dump(res_summary, f, indent=2)

    print(f'\n[DONE {version.upper()}] Accuracy: {acc*100:.2f}% | Macro F1: {np.mean(f1_list):.4f}')
    print('Confusion Matrix (Rows=True, Cols=Pred):')
    print(cm)
    print(f'Saved to: {out_file}')
    return res_summary

if __name__ == '__main__':
    v_to_run = sys.argv[1] if len(sys.argv) > 1 else 'v6'
    if v_to_run == 'v6':
        run_eval_for_model('v6', 'weights/phone_defect_model_v6_best.pt')
    elif v_to_run == 'v7':
        run_eval_for_model('v7', 'weights/phone_defect_model_v7_best.pt')
    elif v_to_run == 'v5':
        run_eval_for_model('v5', 'weights/phone_defect_model_v5_best.pt')
    elif v_to_run == 'all':
        run_eval_for_model('v5', 'weights/phone_defect_model_v5_best.pt')
        run_eval_for_model('v6', 'weights/phone_defect_model_v6_best.pt')
        run_eval_for_model('v7', 'weights/phone_defect_model_v7_best.pt')
