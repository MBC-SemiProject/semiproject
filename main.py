from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
import numpy as np
import os

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "backend", "models", "model.pkl")

try:
    model, feature_cols = joblib.load("models/model.pkl")
except Exception as e:
    print(f"에러 발생: {e}")

# 클라이언트에서 예측을 요청할 때 보낼 데이터 구조(semi.ipynb참조)
class ItemPredictionRequest(BaseModel):
    daily_demand: float
    demand_std_dev: float
    item_popularity_score: float
    stock_level: int
    reorder_point: int
    lead_time_days: int
    holding_cost_per_unit_day: float
    unit_price: float
    category: str
    zone: str
    cluster: int

# 3. 7일 뒤 수요 예측 API 엔드포인트
@app.post("/api/predict")
def predict_demand(data: ItemPredictionRequest):
    try:
        # 1) 입력받은 데이터를 DataFrame으로 변환
        input_data = data()
        df_input = pd.DataFrame([input_data])
        
        # 2) 학습 때와 똑같이 카테고리/장소 원핫 인코딩 처리
        df_encoded = pd.get_dummies(df_input, columns=['category', 'zone'], drop_first=False)
        
        # 3) 모델이 학습할 때 사용했던 18개 피처 컬럼을 그대로 맞추고 없는 컬럼은 0으로 채우기
        for col in feature_cols:
            if col not in df_encoded.columns:
                df_encoded[col] = 0
                
        # 순서도 학습 때와 정확히 일치시키기
        X_pred = df_encoded[feature_cols]
        
        # 4) AI 모델 예측 실행
        predicted_value = model.predict(X_pred)[0]
        
        return {
            "status": "success",
            "forecasted_demand_next_7d": round(float(predicted_value), 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))