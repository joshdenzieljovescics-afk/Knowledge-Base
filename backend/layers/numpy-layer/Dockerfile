FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install numpy==1.26.4 openpyxl==3.1.2 -t /opt/python

CMD ["echo", "Layer built"]
