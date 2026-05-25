import os
import uuid
from flask import Flask, request, jsonify
import boto3
from werkzeug.security import generate_password_hash

app = Flask(__name__)

# 1. Initialize the DynamoDB resource
# It uses the eu-west-1 region to match your Terraform setup
dynamodb = boto3.resource('dynamodb', region_name=os.getenv('AWS_REGION', 'eu-west-1'))
table_name = os.getenv('DYNAMODB_TABLE', 'prima-user-db')
table = dynamodb.Table(table_name)

@app.route('/')
def hello_world():
    return "Hello John"

# 2. Add the POST route
@app.route('/users', methods=['POST'])
def create_user():
    # Parse the incoming JSON payload
    data = request.get_json()

    # Validate that all required fields were provided
    required_fields = ['first_name', 'last_name', 'username', 'password']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    # Generate a unique ID for the DynamoDB 'id' partition key
    user_id = str(uuid.uuid4())
    
    # Hash the password for security
    hashed_password = generate_password_hash(data['password'])

    try:
        # Write the data to DynamoDB
        table.put_item(
            Item={
                'id': user_id,
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'username': data['username'],
                'password_hash': hashed_password
            }
        )
        
        return jsonify({
            "message": "User created successfully",
            "id": user_id
        }), 201

    except Exception as e:
        print(f"Database error: {str(e)}")
        return jsonify({"error": "Failed to create user"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)