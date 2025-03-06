import os
import pandas as pd

# 아이콘 파일명이 저장된 엑셀 파일 경로
excel_path = 'C:/Users/suholee/Downloads/icon_filename_mapping_unique.xlsx'

# 아이콘 이미지가 있는 폴더 경로
icons_path = 'C:/Users/suholee/Desktop/new/icons/'

# 데이터 읽기
df = pd.read_excel(excel_path)

# 파일명 변경
for idx, row in df.iterrows():
    original_name = row['기존 이름']
    new_name = row['새 이름']

    original_path = os.path.join(icons_path, original_name)
    new_path = os.path.join(icons_path, new_name)

    # 파일명 변경
    if os.path.exists(original_path):
        os.rename(original_path, new_path)
        print(f"Renamed: {original_name} → {new_name}")
    else:
        print(f"File not found: {original_name}")
