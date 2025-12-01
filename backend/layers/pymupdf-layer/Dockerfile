FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install PyMuPDF==1.24.0 -t /opt/python

CMD ["echo", "Layer built"]
