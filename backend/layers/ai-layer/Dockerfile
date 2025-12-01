FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install openai==1.57.2 weaviate-client==4.9.3 -t /opt/python

CMD ["echo", "Layer built"]
