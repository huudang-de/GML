import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
import lightgbm as lgb
import xgboost as xgb
import optuna
import warnings

# Tắt cảnh báo Convergence của Logistic Regression trong môi trường test
warnings.filterwarnings("ignore")

def get_models():
    """Khởi tạo 3 mô hình: Baseline (Logistic), Champion (LightGBM) và Alternative (XGBoost)"""
    models = {
        'Logistic Regression (Baseline)': LogisticRegression(class_weight='balanced', max_iter=500, random_state=42),
        'LightGBM (Champion)': lgb.LGBMClassifier(class_weight='balanced', random_state=42, verbose=-1),
        'XGBoost (Alternative)': xgb.XGBClassifier(random_state=42, eval_metric='mlogloss', use_label_encoder=False)
    }
    return models

def evaluate_models(X, y, models):
    """Chạy đối đầu Benchmark bằng Stratified 5-Fold Cross Validation"""
    results = {}
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    for name, model in models.items():
        scores = cross_val_score(model, X, y, cv=cv, scoring='f1_macro', n_jobs=-1)
        results[name] = np.mean(scores)
    return results

def tune_lightgbm(X, y, n_trials=10):
    """Sử dụng thuật toán TPE của Optuna để tối ưu siêu tham số"""
    
    def objective(trial):
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 200),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'num_leaves': trial.suggest_int('num_leaves', 15, 63),
            'max_depth': trial.suggest_int('max_depth', 3, 8),
            'class_weight': 'balanced',
            'random_state': 42,
            'verbose': -1
        }
        
        model = lgb.LGBMClassifier(**params)
        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        score = cross_val_score(model, X, y, cv=cv, scoring='f1_macro', n_jobs=-1).mean()
        return score
        
    optuna.logging.set_verbosity(optuna.logging.WARNING) # Giảm log rác
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials)
    
    return study.best_params, study.best_value
