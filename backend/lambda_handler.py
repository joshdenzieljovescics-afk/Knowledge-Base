"""
AWS Lambda handler for the Knowledge Base FastAPI application.
Uses Mangum to adapt FastAPI for AWS Lambda + API Gateway.
"""
from mangum import Mangum
from app import create_app

# Create the FastAPI app
app = create_app()

# Create the Lambda handler
# lifespan="off" is recommended for Lambda to avoid startup/shutdown lifecycle issues
handler = Mangum(app, lifespan="off")
