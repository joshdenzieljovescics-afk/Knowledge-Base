FROM public.ecr.aws/lambda/python:3.11

RUN mkdir -p /opt/python
RUN pip install fastapi==0.115.5 uvicorn[standard]==0.32.1 python-multipart==0.0.20 pydantic==2.10.3 pydantic-settings==2.6.1 mangum==0.18.0 -t /opt/python

CMD ["echo", "Layer built"]
