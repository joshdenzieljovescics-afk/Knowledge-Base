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
=======
AWS Lambda handler for FastAPI application.
This module wraps the FastAPI app with Mangum to make it compatible with AWS Lambda.
"""
from mangum import Mangum
from app import app

# Create Lambda handler using Mangum
# Mangum is an adapter for running ASGI applications (FastAPI) in AWS Lambda
handler = Mangum(app, lifespan="off")

# The handler function is automatically invoked by AWS Lambda
# It converts API Gateway events to ASGI format and back
>>>>>>> Stashed changes
