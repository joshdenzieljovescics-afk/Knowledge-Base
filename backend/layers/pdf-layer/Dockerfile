FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install PyMuPDF==1.24.0 pdfplumber==0.11.4 pillow==10.3.0 numpy==1.26.4 openpyxl==3.1.2 -t /opt/python

CMD ["echo", "Layer built"]
