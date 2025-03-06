import os
import cv2
import torch
import clip
from PIL import Image
import numpy as np
import time

# 실행 시작 시간 기록
start_time = time.time()

# 사용할 디바이스 선택 (GPU 있으면 GPU 사용)
device = "cuda" if torch.cuda.is_available() else "cpu"

# CLIP 모델과 전처리 함수 불러오기 #ViT-B/32, ViT-L/14
model, preprocess = clip.load("ViT-L/14", device=device)

# 기준 이미지 로드 (PIL 이미지, RGB 변환)
target_image_path = "page165_icon4.jpeg"  # 기준 이미지 파일 경로
target_image = Image.open(target_image_path).convert("RGB")
target_input = preprocess(target_image).unsqueeze(0).to(device)

# 기준 이미지 임베딩 추출 및 정규화
with torch.no_grad():
    target_embedding = model.encode_image(target_input)
target_embedding /= target_embedding.norm(dim=-1, keepdim=True)

# 비교할 이미지들이 저장된 폴더 경로
folder_path = "./icons"

# 결과를 저장할 리스트 (각 항목: (파일명, 유사도))
results = []

# 폴더 내 모든 이미지 파일에 대해 반복
for filename in os.listdir(folder_path):
    if not (filename.lower().endswith(".png") or filename.lower().endswith(".jpg")):
        continue
    image_path = os.path.join(folder_path, filename)
    
    # OpenCV로 이미지 로드
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        continue
    
    # 아이콘 영역 검출을 위한 전처리: 그레이스케일 변환 및 Otsu 이진화
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 컨투어 검출: 외부 윤곽선만 가져오기
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 해당 이미지 내 각 아이콘 후보 영역에 대해 유사도 측정
    icon_similarities = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        # 너무 작은 영역은 잡음으로 간주하여 제외
        if w < 10 or h < 10:
            continue
        
        # 후보 영역을 잘라내기
        crop = img_cv[y:y+h, x:x+w]
        crop_pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        
        # 전처리 및 임베딩 계산
        crop_input = preprocess(crop_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            crop_embedding = model.encode_image(crop_input)
        crop_embedding /= crop_embedding.norm(dim=-1, keepdim=True)
        
        # 코사인 유사도 계산 (내적)
        similarity = (target_embedding @ crop_embedding.T).item()
        icon_similarities.append(similarity)
    
    # 한 이미지 내에서 여러 아이콘 후보가 있다면, 최대 유사도를 해당 이미지의 유사도로 사용
    if icon_similarities:
        image_similarity = max(icon_similarities)
    else:
        image_similarity = 0  # 아이콘 후보가 없으면 0으로 처리
    
    results.append((image_path, image_similarity))
    print(f"[{image_path}] 최대 아이콘 유사도: {image_similarity:.4f}")

# 유사도가 높은 순(내림차순)으로 정렬
results.sort(key=lambda x: x[1], reverse=True)

print("\n유사도가 높은 순으로 정렬된 결과:")
for path, similarity in results:
    print(f"{path}: {similarity:.4f}")

# 전체 실행 시간 측정 및 출력
end_time = time.time()
print(f"\n전체 실행 시간: {end_time - start_time:.2f} 초")
