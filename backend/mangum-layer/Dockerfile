FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install mangum==0.17.0 -t /opt/python

CMD ["echo", "Layer built successfully"]
