import os
import io
import textwrap
import re
import requests
from flask import Flask,request,jsonify
from pypdf import PdfReader
from pdfminer.high_level import extract_text

app = Flask(__name__)

class PO_num_extracter:
    
    def __init__(self,pdf_path_or_url : str):
        self.pdf_path_or_url = pdf_path_or_url
        self.flag = bool
    
    def log(self,message:str,success_flag=True):
        if success_flag: print(f"\n\n###################   {message}   ###################")
        else: print(f"!!!!!!!!!!!!!!!!!!   {message}   !!!!!!!!!!!!!!!!!!!!") 
        
    def format_text(self, raw_text: str):
        formatted_text = ' '.join(raw_text.split())
        formatted_text = ''.join(char if char.isalnum() or char.isspace() else ' ' for char in formatted_text)
        sections = formatted_text.split('   ')
        formatted_text = ' '.join(section.strip() for section in sections if section.strip())
        return formatted_text.strip()
    
    def download_pdf(self):
        if self.pdf_path_or_url.startswith("http"):
            self.log("Downloading Pdf")
            response = requests.get(self.pdf_path_or_url)
            if response.status_code == 200:
                self.flag = True
                return response.content
                
            else:
                raise ValueError(f"Failed to download PDF from {self.pdf_path_or_url}")
        else:
            with open(self.pdf_path_or_url, 'rb') as f:
                return f.read()
            
    def extract_data(self):
    
        pdf_data = self.download_pdf()
        
        reader = PdfReader(io.BytesIO(pdf_data))
        text = ''.join([page.extract_text() for page in reader.pages])
        self.wrapped_text = textwrap.fill(text, width=120)
        
        if not self.flag:
            
            self.text = extract_text(self.pdf_path_or_url)
        
            return [self.wrapped_text,self.text]
        else: return [self.wrapped_text]
    
    def extract_invoice_number(self,text: str):
        
        invoice_numbers = re.findall(r'\b\d{5}\b', text)
        if invoice_numbers: return invoice_numbers
        else:
            pattern = r'(?:invoice\s*(?:no(?:\.|:)?|number|num)?\s*:?)(\d{5})'
            invoice_numbers = re.search(pattern, text, re.IGNORECASE)
            if invoice_numbers:
                return invoice_numbers.group()
            else:
                return
    
    def main(self):
        texts = self.extract_data()
        invoice_numbers = []
        # print(texts[0])
        for text in texts:
            if self.extract_invoice_number(text):
                invoice_numbers.append(self.extract_invoice_number(text)[0])
                
        return invoice_numbers[0] if invoice_numbers else None
    
    
@app.route("/extractPO",methods=['POST'])
def extractor():
        # Check if request data is JSON
    if request.is_json:
        data = request.json
        pth_url = data.get('path_url')
        if pth_url:
            obj = PO_num_extracter(pth_url)
            # print("Invoice number :",obj.main())
            invoice_num = obj.main()
            return jsonify({'invoice_no': invoice_num}), 200
    else:
        return jsonify({'error': 'String parameter is missing'}), 400
    
@app.route("/get_text",methods=['POST'])
def text_parser():
        # Check if request data is JSON
    if request.is_json:
        data = request.json
        pth_url = data.get('path_url')
        if pth_url:
            obj = PO_num_extracter(pth_url)
            invoice_num = obj.extract_data()
            return jsonify({'text': invoice_num[0]}), 200
    else:
        return jsonify({'error': 'String parameter is missing'}), 400
    
if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
