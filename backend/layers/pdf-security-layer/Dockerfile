FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install pdfplumber==0.11.4 pillow==10.3.0 python-jose[cryptography]==3.3.0 python-dotenv==1.0.1 -t /opt/python

CMD ["echo", "Layer built"]
