#!/usr/bin/env python3
import sys
from PyPDF2 import PdfReader, PdfWriter

def split_pdf(input_path, pages_per_split, output_prefix):
    # PDF 파일 읽기
    reader = PdfReader(input_path)
    total_pages = len(reader.pages)
    print(f"총 페이지 수: {total_pages}")
    
    # 분할 파일 개수 계산 (올림 처리)
    num_splits = (total_pages + pages_per_split - 1) // pages_per_split
    
    for i in range(num_splits):
        writer = PdfWriter()
        start = i * pages_per_split
        end = min(start + pages_per_split, total_pages)
        
        # start 부터 end 페이지까지 추가
        for page_num in range(start, end):
            writer.add_page(reader.pages[page_num])
        
        output_filename = f"./pdfs/{output_prefix}{i+1}.pdf"
        with open(output_filename, "wb") as output_file:
            writer.write(output_file)
        print(f"'{output_filename}' 저장됨: 페이지 {start+1} ~ {end}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python split_pdf.py <입력_pdf파일> [페이지 수 (기본:200)]")
        sys.exit(1)
    
    input_pdf = sys.argv[1]
    pages_per_split = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    split_pdf(input_pdf, pages_per_split, input_pdf[:-4] + "_")
